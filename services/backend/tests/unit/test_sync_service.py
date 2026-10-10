"""Regression tests for the hardened sync state machine and candidate handoff.

New-event governance and exact matching have focused coverage in
``test_external_candidate_ingestion.py``. Existing linked-event behavior
remains independently tested here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sync_service import (
    SyncResult,
    _get_connector,
    _has_significant_deviation,
    run_sync,
)
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.models.event_instance import (
    EventInstance,
    EventSource,
    EventVisibility,
    SyncState,
)
from app.domain.models.external_event_link import ExternalEventLink, ExternalEventLinkState
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnectorError
from app.domain.services.sync_policy import INTERNAL_DELETE_MARKER

_NOW = datetime(2026, 3, 6, 12, tzinfo=UTC)
_DISTRICT_ID = uuid.uuid4()
_CONG_ID = uuid.uuid4()
_INT_ID = uuid.uuid4()
_START = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
_END = datetime(2026, 4, 10, 10, 0, tzinfo=UTC)


def _hash(
    uid: str, start_at=..., end_at=..., title: str = "Gottesdienst",
    description: str | None = "Beschreibung", is_cancelled: bool = False,
) -> str:
    import hashlib

    if start_at is ...:
        start_at = _START
    if end_at is ...:
        end_at = _END
    raw_str = f"{uid}|{start_at}|{end_at}|{title}|{description}|{is_cancelled}"
    return hashlib.sha256(raw_str.encode()).hexdigest()


def _integration(**kw) -> CalendarIntegration:
    return CalendarIntegration(
        id=kw.get("id", _INT_ID), district_id=kw.get("district_id", _DISTRICT_ID),
        congregation_id=kw.get("congregation_id", _CONG_ID), name="Test Kalender",
        type=CalendarType.ICS, credentials_enc="encrypted", sync_interval=60,
        capabilities=[CalendarCapability.READ], is_active=True, last_synced_at=None,
        created_at=_NOW, updated_at=_NOW, last_sync_error=None,
    )


def _raw(
    uid: str = "uid@test", title: str = "Gottesdienst",
    description: str = "Beschreibung", is_cancelled: bool = False,
    start_at: datetime = _START, end_at: datetime = _END,
) -> RawCalendarEvent:
    return RawCalendarEvent(
        uid=uid, title=title, start_at=start_at, end_at=end_at,
        description=description,
        content_hash=_hash(
            uid, start_at=start_at, end_at=end_at, title=title,
            description=description, is_cancelled=is_cancelled,
        ),
        is_cancelled=is_cancelled,
    )


def _make_event_instance(**kw) -> EventInstance:
    return EventInstance.create(
        planning_slot_id=kw.get("planning_slot_id", uuid.uuid4()),
        title=kw.get("title", "Gottesdienst"),
        actual_start_at=kw.get("actual_start_at", _START),
        actual_end_at=kw.get("actual_end_at", _END),
        source=EventSource.EXTERNAL, visibility=EventVisibility.PUBLIC,
        content_hash=kw.get("content_hash"), instance_id=kw.get("instance_id"),
    )


def _make_link(**kw) -> ExternalEventLink:
    return ExternalEventLink.create(
        event_instance_id=kw.get("event_instance_id", uuid.uuid4()),
        provider=CalendarType.ICS.value,
        external_event_id=kw.get("uid", "uid@test"),
        calendar_integration_id=_INT_ID,
        last_synced_hash=kw.get("last_synced_hash"),
    )


def _make_slot(**kw) -> PlanningSlot:
    return PlanningSlot.create(
        district_id=_DISTRICT_ID,
        planning_date=kw.get("planning_date", _START.date()),
        planning_time=kw.get("planning_time", _START.time()),
        congregation_id=kw.get("congregation_id", _CONG_ID),
        category="Gottesdienst", title="Gottesdienst",
    )


@pytest.fixture
def mocks():
    """Patch only linked-event sync dependencies; candidate tests mock their ports."""
    link_repo = AsyncMock()
    instance_repo = AsyncMock()
    slot_repo = AsyncMock()
    integration_repo = AsyncMock()
    connector = MagicMock()
    connector.fetch_events = AsyncMock(return_value=[])
    connector.authoritative_snapshot = False
    connector.window_bounded_snapshot = False  # full-feed semantics like ICS
    patchers = [
        patch("app.application.sync_service.SqlExternalEventLinkRepository", return_value=link_repo),
        patch("app.application.sync_service.SqlEventInstanceRepository", return_value=instance_repo),
        patch("app.application.sync_service.SqlPlanningSlotRepository", return_value=slot_repo),
        patch("app.application.sync_service.SqlCalendarIntegrationRepository", return_value=integration_repo),
        patch("app.application.sync_service._get_connector", return_value=connector),
        patch(
            "app.application.sync_service.decrypt_credentials",
            MagicMock(return_value={"url": "https://example.com/cal.ics"}),
        ),
    ]
    for patcher in patchers:
        patcher.start()
    slot_repo.get.return_value = None
    slot_repo.list_for_date_range = AsyncMock(return_value=[])
    yield {
        "link_repo": link_repo, "instance_repo": instance_repo,
        "slot_repo": slot_repo, "integration_repo": integration_repo,
        "connector": connector, "session": AsyncMock(spec=AsyncSession),
    }
    for patcher in patchers:
        patcher.stop()


class TestRunSync:
    @pytest.mark.parametrize("hard_delete", [False, True])
    async def test_cancel_with_unchanged_hash_and_duplicate_delivery(self, mocks, hard_delete):
        from app.domain.models.calendar_integration import SyncDeleteMode

        integration = _integration()
        integration.delete_behavior = (
            SyncDeleteMode.HARD_DELETE if hard_delete else SyncDeleteMode.MARK_CANCELLED
        )
        slot = _make_slot()
        instance = _make_event_instance(planning_slot_id=slot.id)
        link = _make_link(event_instance_id=instance.id, last_synced_hash=_hash("uid@test"))
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [_raw(is_cancelled=True)]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        assert (await run_sync(_INT_ID, mocks["session"])).cancelled == 1
        assert (await run_sync(_INT_ID, mocks["session"])).cancelled == 0
        assert (await run_sync(_INT_ID, mocks["session"])).skipped == 1
        if hard_delete:
            assert link.event_instance_id is None
            assert link.state == ExternalEventLinkState.SYNC_TOMBSTONE
            mocks["slot_repo"].delete.assert_awaited_once_with(slot.id)
        else:
            assert slot.status == PlanningSlotStatus.CANCELLED

    async def test_released_event_survives_provider_hard_delete(self, mocks):
        from app.domain.models.calendar_integration import SyncDeleteMode
        from app.domain.models.planning_slot import EventApprovalStatus

        integration = _integration()
        integration.delete_behavior = SyncDeleteMode.HARD_DELETE
        slot = _make_slot()
        slot.approval_status = EventApprovalStatus.CONFIRMED
        slot.released_at = datetime.now(UTC)
        instance = _make_event_instance(planning_slot_id=slot.id)
        link = _make_link(event_instance_id=instance.id, last_synced_hash=_hash("uid@test"))
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [_raw(is_cancelled=True)]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot

        result = await run_sync(_INT_ID, mocks["session"])
        assert result.cancelled == 1
        assert slot.status == PlanningSlotStatus.CANCELLED
        assert link.event_instance_id == instance.id
        mocks["slot_repo"].delete.assert_not_awaited()
        mocks["slot_repo"].save.assert_awaited()

    async def test_provider_hard_delete_keeps_confirmed_event_as_cancelled(self, mocks):
        from app.domain.models.calendar_integration import SyncDeleteMode
        from app.domain.models.planning_slot import EventApprovalStatus

        integration = _integration()
        integration.delete_behavior = SyncDeleteMode.HARD_DELETE
        slot = _make_slot()
        slot.approval_status = EventApprovalStatus.CONFIRMED
        slot.released_at = datetime.now(UTC)
        instance = _make_event_instance(planning_slot_id=slot.id)
        link = _make_link(event_instance_id=instance.id, last_synced_hash=_hash("uid@test"))
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [_raw(is_cancelled=True)]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot

        result = await run_sync(_INT_ID, mocks["session"])
        assert result.cancelled == 1
        assert slot.status == PlanningSlotStatus.CANCELLED
        assert link.event_instance_id == instance.id
        mocks["slot_repo"].delete.assert_not_awaited()
        mocks["slot_repo"].save.assert_awaited_once_with(slot)

    async def test_snapshot_hard_delete_keeps_confirmed_event_as_cancelled(self, mocks):
        from app.domain.models.calendar_integration import SyncDeleteMode
        from app.domain.models.planning_slot import EventApprovalStatus

        integration = _integration()
        integration.delete_behavior = SyncDeleteMode.HARD_DELETE
        slot = _make_slot()
        slot.approval_status = EventApprovalStatus.CONFIRMED
        slot.released_at = datetime.now(UTC)
        start = _NOW + timedelta(days=30)
        instance = _make_event_instance(
            planning_slot_id=slot.id, actual_start_at=start,
            actual_end_at=start + timedelta(hours=1),
        )
        link = _make_link(event_instance_id=instance.id)
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].authoritative_snapshot = True
        mocks["link_repo"].list_active_by_integration.return_value = [link]
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot

        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert result.cancelled == 1
        assert slot.status == PlanningSlotStatus.CANCELLED
        assert link.event_instance_id == instance.id
        mocks["slot_repo"].delete.assert_not_awaited()
        mocks["slot_repo"].save.assert_awaited_once_with(slot)

    async def test_connector_error_isolates_event_and_continues(self, mocks):
        integration = _integration()
        integration.capabilities.append(CalendarCapability.WRITE)
        slot = _make_slot()
        slot.status = PlanningSlotStatus.CANCELLED
        instance = _make_event_instance(planning_slot_id=slot.id)
        instance.sync_state = SyncState.DIRTY_INTERNAL
        failing_link = _make_link(
            event_instance_id=instance.id, uid="uid@test",
            last_synced_hash=_hash("uid@test"),
        )
        healthy_slot = _make_slot()
        healthy_instance = _make_event_instance(planning_slot_id=healthy_slot.id)
        healthy_link = _make_link(event_instance_id=healthy_instance.id, uid="other@test")
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [_raw(), _raw(uid="other@test")]
        mocks["connector"].delete_event = AsyncMock(side_effect=CalendarConnectorError("HTTP 412"))

        async def get_link(provider, external_event_id, calendar_integration_id):
            if external_event_id == "uid@test":
                return failing_link
            return healthy_link

        mocks["link_repo"].get_by_external_event.side_effect = get_link

        async def get_instance(iid):
            if iid == instance.id:
                return instance
            return healthy_instance

        mocks["instance_repo"].get.side_effect = get_instance

        async def get_slot(sid):
            if sid == slot.id:
                return slot
            return healthy_slot

        mocks["slot_repo"].get.side_effect = get_slot
        result = await run_sync(_INT_ID, mocks["session"])
        assert result.failed == 1
        assert result.skipped == 0
        assert result.updated == 1
        assert failing_link.revision_marker != INTERNAL_DELETE_MARKER
        assert healthy_link.last_synced_hash not in (None, failing_link.last_synced_hash)

    @pytest.mark.parametrize("cancelled", [False, True])
    async def test_concurrent_edits_preserve_internal_data(self, mocks, cancelled):
        instance = _make_event_instance(title="Internal edit")
        instance.sync_state = SyncState.DIRTY_INTERNAL
        link = _make_link(event_instance_id=instance.id, last_synced_hash="acknowledged")
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [_raw(is_cancelled=cancelled)]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        await run_sync(_INT_ID, mocks["session"])
        assert instance.title == "Internal edit"
        assert instance.sync_state == SyncState.CONFLICT
        assert link.last_synced_hash == "acknowledged"
        mocks["slot_repo"].delete.assert_not_awaited()

    async def test_internal_cancel_is_pushed_once(self, mocks):
        integration = _integration()
        integration.capabilities.append(CalendarCapability.WRITE)
        slot = _make_slot()
        slot.status = PlanningSlotStatus.CANCELLED
        instance = _make_event_instance(planning_slot_id=slot.id)
        instance.sync_state = SyncState.DIRTY_INTERNAL
        link = _make_link(event_instance_id=instance.id, last_synced_hash=_hash("uid@test"))
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [_raw()]
        mocks["connector"].delete_event = AsyncMock()
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        await run_sync(_INT_ID, mocks["session"])
        await run_sync(_INT_ID, mocks["session"])
        mocks["connector"].delete_event.assert_awaited_once()
        assert link.revision_marker == "internal:deleted"

    async def test_internal_cancel_with_remote_edit_preserves_provider_event(self, mocks):
        integration = _integration()
        integration.capabilities.append(CalendarCapability.WRITE)
        slot = _make_slot()
        slot.status = PlanningSlotStatus.CANCELLED
        instance = _make_event_instance(planning_slot_id=slot.id)
        instance.sync_state = SyncState.DIRTY_INTERNAL
        link = _make_link(event_instance_id=instance.id, last_synced_hash="acknowledged")
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [_raw(title="Remote edit")]
        mocks["connector"].delete_event = AsyncMock()
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        result = await run_sync(_INT_ID, mocks["session"])
        assert result.skipped == 1
        assert instance.sync_state == SyncState.CONFLICT
        assert link.last_synced_hash == "acknowledged"
        mocks["connector"].delete_event.assert_not_awaited()

    async def test_external_time_change_sets_deviation_without_moving_slot(self, mocks):
        from datetime import time

        slot = _make_slot(planning_time=time(7))
        instance = _make_event_instance(planning_slot_id=slot.id)
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [_raw()]
        mocks["link_repo"].get_by_external_event.return_value = _make_link(event_instance_id=instance.id)
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        await run_sync(_INT_ID, mocks["session"])
        assert instance.deviation_flag
        assert slot.planning_time == time(7)

    async def test_integration_not_found_raises(self, mocks):
        mocks["integration_repo"].get.return_value = None
        with pytest.raises(ValueError, match=str(_INT_ID)):
            await run_sync(_INT_ID, mocks["session"])
        mocks["integration_repo"].get.assert_awaited_once_with(_INT_ID)

    async def test_new_event_hands_off_to_candidate_ingestion(self, mocks):
        raw = _raw()
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = None
        with patch(
            "app.application.sync_service.import_candidate_or_match", new_callable=AsyncMock,
            return_value=False,
        ) as handoff:
            result = await run_sync(_INT_ID, mocks["session"])
        assert result == SyncResult(skipped=1)
        handoff.assert_awaited_once()
        assert handoff.await_args.kwargs["raw"] == raw
        mocks["slot_repo"].save.assert_not_awaited()
        mocks["instance_repo"].save.assert_not_awaited()

    async def test_new_event_counts_safe_auto_match(self, mocks):
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [_raw()]
        mocks["link_repo"].get_by_external_event.return_value = None
        with patch(
            "app.application.sync_service.import_candidate_or_match", new_callable=AsyncMock,
            return_value=True,
        ):
            result = await run_sync(_INT_ID, mocks["session"])
        assert result == SyncResult(auto_matched=1)

    async def test_acknowledged_cancel_is_write_free(self, mocks):
        raw = _raw(is_cancelled=True)
        instance = _make_event_instance()
        link = _make_link(
            event_instance_id=instance.id,
            last_synced_hash=_hash(raw.uid, is_cancelled=True),
        )
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = _make_slot()
        result = await run_sync(_INT_ID, mocks["session"])
        assert result.skipped == 1
        mocks["instance_repo"].save.assert_not_called()
        mocks["slot_repo"].save.assert_not_called()
        mocks["slot_repo"].delete.assert_not_called()
        mocks["link_repo"].save.assert_not_called()

    async def test_changed_event_updates_instance(self, mocks):
        instance = _make_event_instance(content_hash="old-hash")
        expected_hash = _hash("uid@test", title="Neuer Titel")
        link = _make_link(event_instance_id=instance.id, last_synced_hash="old-hash")
        raw = _raw(title="Neuer Titel")
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        result = await run_sync(_INT_ID, mocks["session"])
        assert result == SyncResult(updated=1)
        mocks["link_repo"].get_by_external_event.assert_awaited_once_with(
            provider=CalendarType.ICS.value, external_event_id=raw.uid,
            calendar_integration_id=_INT_ID,
        )
        mocks["instance_repo"].get.assert_awaited_once_with(link.event_instance_id)
        assert instance.title == "Neuer Titel"
        assert instance.content_hash == expected_hash
        assert instance.sync_state == SyncState.DIRTY_EXTERNAL
        mocks["instance_repo"].save.assert_awaited_once_with(instance)
        assert link.last_synced_hash == expected_hash
        mocks["link_repo"].save.assert_awaited_once_with(link)

    async def test_unchanged_event_skipped(self, mocks):
        instance = _make_event_instance()
        link = _make_link(event_instance_id=instance.id, last_synced_hash=_hash("uid@test"))
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [_raw()]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        assert await run_sync(_INT_ID, mocks["session"]) == SyncResult(skipped=1)
        mocks["instance_repo"].save.assert_not_called()
        mocks["link_repo"].save.assert_not_called()
        mocks["slot_repo"].save.assert_not_called()

    async def test_existing_cancelled_event_cancels_slot(self, mocks):
        slot = _make_slot()
        instance = _make_event_instance(planning_slot_id=slot.id)
        link = _make_link(event_instance_id=instance.id)
        raw = _raw(is_cancelled=True)
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        assert await run_sync(_INT_ID, mocks["session"]) == SyncResult(cancelled=1)
        assert slot.status == PlanningSlotStatus.CANCELLED
        mocks["slot_repo"].save.assert_awaited_once_with(slot)
        assert instance.sync_state == SyncState.CLEAN
        mocks["instance_repo"].save.assert_not_called()

    async def test_last_synced_at_updated(self, mocks):
        integration = _integration()
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = []
        await run_sync(_INT_ID, mocks["session"])
        assert integration.last_synced_at is not None
        mocks["integration_repo"].save.assert_awaited_once_with(integration)

    def test_get_connector_rejects_unsupported_calendar_type(self):
        with pytest.raises(NotImplementedError, match="No connector implemented"):
            _get_connector("UNSUPPORTED")  # type: ignore[arg-type]


class TestGetConnector:
    def test_dispatches_ics(self):
        from app.adapters.calendar.ical_connector import ICalConnector

        assert isinstance(_get_connector(CalendarType.ICS), ICalConnector)

    def test_dispatches_caldav(self):
        from app.adapters.calendar.caldav_connector import CalDAVConnector

        assert isinstance(_get_connector(CalendarType.CALDAV), CalDAVConnector)

    def test_dispatches_google(self):
        from app.adapters.calendar.google_connector import GoogleCalendarConnector

        assert isinstance(_get_connector(CalendarType.GOOGLE), GoogleCalendarConnector)

    def test_dispatches_microsoft(self):
        from app.adapters.calendar.microsoft_connector import MicrosoftGraphCalendarConnector

        assert isinstance(_get_connector(CalendarType.MICROSOFT), MicrosoftGraphCalendarConnector)


class TestHasSignificantDeviation:
    def test_no_deviation_within_five_minutes(self):
        slot = _make_slot(planning_time=_START.time())
        assert _has_significant_deviation(
            slot, _START + timedelta(minutes=4), _END + timedelta(minutes=34)
        ) is False

    def test_deviation_beyond_five_minutes(self):
        slot = _make_slot(planning_time=_START.time())
        assert _has_significant_deviation(
            slot, _START + timedelta(minutes=6), _END + timedelta(minutes=36)
        ) is True

    def test_end_only_deviation(self):
        slot = _make_slot(planning_time=_START.time())
        assert _has_significant_deviation(slot, _START, _END + timedelta(minutes=36)) is True

    def test_configured_duration_replaces_default(self, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "sync_expected_duration_minutes", 60)
        slot = _make_slot(planning_time=_START.time())
        assert _has_significant_deviation(slot, _START, _END) is False
        monkeypatch.setattr(settings, "sync_expected_duration_minutes", 120)
        assert _has_significant_deviation(slot, _START, _END) is True


async def test_non_overlapping_soft_changes_merge_without_conflict(mocks):
    instance = _make_event_instance(title="Internal title")
    instance.description = "Beschreibung"
    instance.sync_state = SyncState.DIRTY_INTERNAL
    link = _make_link(event_instance_id=instance.id, last_synced_hash="old")
    link.last_synced_payload = {
        "title": "Gottesdienst", "description": "Beschreibung",
        "actual_start_at": _START.isoformat(), "actual_end_at": _END.isoformat(),
    }
    mocks["integration_repo"].get.return_value = _integration()
    mocks["connector"].fetch_events.return_value = [_raw(description="Remote description")]
    mocks["link_repo"].get_by_external_event.return_value = link
    mocks["instance_repo"].get.return_value = instance
    result = await run_sync(_INT_ID, mocks["session"])
    assert result.updated == 1
    assert instance.title == "Internal title"
    assert instance.description == "Remote description"
    assert instance.sync_state == SyncState.DIRTY_INTERNAL


async def test_authoritative_snapshot_reconciles_missing_provider_event(mocks):
    slot = _make_slot()
    future_start = datetime.now(UTC) + timedelta(days=1)
    instance = _make_event_instance(
        planning_slot_id=slot.id, actual_start_at=future_start,
        actual_end_at=future_start + timedelta(minutes=90),
    )
    link = _make_link(event_instance_id=instance.id, last_synced_hash="old")
    mocks["integration_repo"].get.return_value = _integration()
    mocks["connector"].authoritative_snapshot = True
    mocks["connector"].fetch_events.return_value = []
    mocks["link_repo"].list_active_by_integration.return_value = [link]
    mocks["instance_repo"].get.return_value = instance
    mocks["slot_repo"].get.return_value = slot
    assert (await run_sync(_INT_ID, mocks["session"])).cancelled == 1
    assert slot.status == PlanningSlotStatus.CANCELLED


async def test_partial_connector_failure_is_reported_separately(mocks):
    integration = _integration()
    integration.capabilities.append(CalendarCapability.WRITE)
    slot = _make_slot()
    slot.status = PlanningSlotStatus.CANCELLED
    instance = _make_event_instance(planning_slot_id=slot.id)
    instance.sync_state = SyncState.DIRTY_INTERNAL
    link = _make_link(event_instance_id=instance.id, last_synced_hash=_hash("uid@test"))
    mocks["integration_repo"].get.return_value = integration
    mocks["connector"].fetch_events.return_value = [_raw()]
    mocks["connector"].delete_event = AsyncMock(side_effect=CalendarConnectorError("provider"))
    mocks["link_repo"].get_by_external_event.return_value = link
    mocks["instance_repo"].get.return_value = instance
    mocks["slot_repo"].get.return_value = slot
    result = await run_sync(_INT_ID, mocks["session"])
    assert result.failed == 1
    assert result.skipped == 0
    assert integration.last_sync_error == "1 calendar event(s) failed during partial sync"


class TestEchoSuppressionPerWritableProvider:
    """Task 4.5: verify update and delete echo suppression for every writable provider.

    After an outbound push (time update or internal delete), the provider echo
    of the pushed state SHALL be recognized as already acknowledged and cause
    no writes on the next inbound sync run — for every writable provider type.
    """

    @pytest.fixture(autouse=True)
    def _all_providers_enabled(self, monkeypatch):
        # GOOGLE/MICROSOFT are disabled in 1.0 (#467) but their connector code is
        # kept for the post-1.0 OAuth work, so its sync semantics stay covered.
        monkeypatch.setattr(
            "app.application.sync_service.SUPPORTED_CALENDAR_TYPES", frozenset(CalendarType)
        )

    @pytest.mark.parametrize("provider", [CalendarType.GOOGLE, CalendarType.MICROSOFT, CalendarType.CALDAV])
    async def test_pushed_time_update_echo_is_suppressed(self, mocks, provider):
        integration = _integration()
        integration.type = provider
        integration.capabilities = [CalendarCapability.READ, CalendarCapability.WRITE]
        slot = _make_slot()
        instance = _make_event_instance(
            planning_slot_id=slot.id,
            actual_start_at=_START + timedelta(hours=1),
            actual_end_at=_END + timedelta(hours=1),
        )
        instance.sync_state = SyncState.DIRTY_INTERNAL
        link = _make_link(
            event_instance_id=instance.id,
            last_synced_hash=_hash("uid@test"),
        )
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [_raw()]
        mocks["connector"].update_event_times = AsyncMock(return_value="rev-1")
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot

        first = await run_sync(_INT_ID, mocks["session"])
        assert first.updated == 1
        assert instance.sync_state == SyncState.CLEAN
        acknowledged_hash = link.last_synced_hash

        mocks["connector"].update_event_times.reset_mock()
        mocks["instance_repo"].save.reset_mock()
        mocks["link_repo"].save.reset_mock()
        mocks["connector"].fetch_events.return_value = [
            _raw(start_at=_START + timedelta(hours=1), end_at=_END + timedelta(hours=1))
        ]
        second = await run_sync(_INT_ID, mocks["session"])
        assert second.skipped == 1
        assert second.updated == 0
        mocks["connector"].update_event_times.assert_not_awaited()
        mocks["instance_repo"].save.assert_not_called()
        assert link.last_synced_hash == acknowledged_hash

    @pytest.mark.parametrize("provider", [CalendarType.GOOGLE, CalendarType.MICROSOFT, CalendarType.CALDAV])
    async def test_pushed_delete_echo_is_suppressed(self, mocks, provider):
        integration = _integration()
        integration.type = provider
        integration.capabilities = [CalendarCapability.READ, CalendarCapability.WRITE]
        slot = _make_slot()
        slot.status = PlanningSlotStatus.CANCELLED
        instance = _make_event_instance(planning_slot_id=slot.id)
        instance.sync_state = SyncState.DIRTY_INTERNAL
        link = _make_link(
            event_instance_id=instance.id,
            last_synced_hash=_hash("uid@test"),
        )
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [_raw()]
        mocks["connector"].delete_event = AsyncMock()
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot

        first = await run_sync(_INT_ID, mocks["session"])
        assert first.cancelled == 1
        assert link.revision_marker == INTERNAL_DELETE_MARKER
        assert link.state == ExternalEventLinkState.SYNC_TOMBSTONE

        mocks["connector"].delete_event.reset_mock()
        mocks["instance_repo"].save.reset_mock()
        mocks["slot_repo"].delete.reset_mock()
        second = await run_sync(_INT_ID, mocks["session"])
        assert second.skipped == 1
        assert second.cancelled == 0
        mocks["connector"].delete_event.assert_not_awaited()
        mocks["instance_repo"].save.assert_not_called()
        mocks["slot_repo"].delete.assert_not_awaited()
        assert link.state == ExternalEventLinkState.SYNC_TOMBSTONE


def _occurrence(recurrence_id: str, **kw) -> RawCalendarEvent:
    from dataclasses import replace

    raw = _raw(uid=f"uid@test::{recurrence_id}", **kw)
    return replace(raw, series_uid="uid@test", recurrence_id=recurrence_id)


class TestSyncWindow:
    """#465: the provider query is bounded and reconciliation stays inside it."""

    async def test_fetch_uses_bounded_configurable_window(self, mocks, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "sync_window_past_days", 62)
        monkeypatch.setattr(settings, "sync_window_future_months", 24)
        mocks["integration_repo"].get.return_value = _integration()
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        kwargs = mocks["connector"].fetch_events.await_args.kwargs
        assert kwargs["from_dt"] == _NOW - timedelta(days=62)
        assert kwargs["to_dt"] == datetime(2028, 3, 6, 12, tzinfo=UTC)

    @pytest.mark.parametrize(
        ("start", "cancelled"),
        [
            (_NOW + timedelta(days=30), 1),  # inside window, missing from feed
            (datetime(2028, 3, 7, tzinfo=UTC), 0),  # after window end
            (_NOW - timedelta(days=63), 0),  # before window start
        ],
    )
    async def test_reconcile_only_inside_window(self, mocks, start, cancelled):
        slot = _make_slot()
        instance = _make_event_instance(
            planning_slot_id=slot.id, actual_start_at=start,
            actual_end_at=start + timedelta(minutes=90),
        )
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].authoritative_snapshot = True
        mocks["link_repo"].list_active_by_integration.return_value = [
            _make_link(event_instance_id=instance.id)
        ]
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert result.cancelled == cancelled
        expected = PlanningSlotStatus.CANCELLED if cancelled else PlanningSlotStatus.ACTIVE
        assert slot.status == expected

    async def test_legacy_series_link_is_rekeyed_to_matching_occurrence(self, mocks):
        """Pre-#465 rows store a series master under its plain UID."""
        slot = _make_slot()
        instance = _make_event_instance(planning_slot_id=slot.id)
        legacy = _make_link(event_instance_id=instance.id, uid="uid@test", last_synced_hash="old")
        occurrence = _occurrence("20260410T090000Z")

        async def by_external_event(*, provider, external_event_id, calendar_integration_id):
            return legacy if external_event_id == legacy.external_event_id else None

        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].authoritative_snapshot = True
        mocks["connector"].fetch_events.return_value = [occurrence]
        mocks["link_repo"].get_by_external_event.side_effect = by_external_event
        mocks["link_repo"].list_active_by_integration.return_value = [legacy]
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert legacy.external_event_id == occurrence.uid
        assert (result.updated, result.cancelled) == (1, 0)
        assert slot.status == PlanningSlotStatus.ACTIVE

    async def test_legacy_link_with_other_start_is_not_rekeyed(self, mocks):
        instance = _make_event_instance()
        legacy = _make_link(event_instance_id=instance.id, uid="uid@test")
        occurrence = _occurrence(
            "20260417T090000Z", start_at=_START + timedelta(days=7), end_at=_END + timedelta(days=7)
        )
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [occurrence]
        mocks["link_repo"].get_by_external_event.side_effect = (
            lambda **kw: legacy if kw["external_event_id"] == "uid@test" else None
        )
        mocks["instance_repo"].get.return_value = instance
        with patch(
            "app.application.sync_service.import_candidate_or_match", AsyncMock(return_value=False)
        ) as ingest:
            await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert legacy.external_event_id == "uid@test"
        ingest.assert_awaited_once()


class TestAuthoritativeConnectors:
    @pytest.mark.parametrize(
        ("calendar_type", "authoritative", "bounded"),
        [
            (CalendarType.ICS, True, False),
            (CalendarType.CALDAV, True, True),
            (CalendarType.MICROSOFT, False, False),
        ],
    )
    def test_snapshot_semantics_per_connector(self, calendar_type, authoritative, bounded):
        from app.application.sync_service import _CONNECTOR_MAP

        connector = _CONNECTOR_MAP[calendar_type]
        assert connector.authoritative_snapshot is authoritative
        assert connector.window_bounded_snapshot is bounded


class TestCodexReviewFindings:
    """Regression tests for the Codex review of PR #483."""

    def _reconcile_setup(self, mocks, *, slot_status=PlanningSlotStatus.ACTIVE):
        slot = _make_slot()
        slot.status = slot_status
        start = _NOW + timedelta(days=30)
        instance = _make_event_instance(
            planning_slot_id=slot.id, actual_start_at=start, actual_end_at=start + timedelta(hours=1),
        )
        raw = _raw(start_at=start, end_at=start + timedelta(hours=1))
        link = _make_link(event_instance_id=instance.id, last_synced_hash=raw.content_hash)
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].authoritative_snapshot = True
        mocks["link_repo"].list_active_by_integration.return_value = [link]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        return slot, instance, link, raw

    async def test_event_restored_after_snapshot_gap_reactivates_slot(self, mocks):
        slot, _, _, raw = self._reconcile_setup(mocks)
        mocks["connector"].fetch_events.return_value = []
        assert (await run_sync(_INT_ID, mocks["session"], now=_NOW)).cancelled == 1
        assert slot.status == PlanningSlotStatus.CANCELLED

        mocks["connector"].fetch_events.return_value = [raw]
        restored = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert slot.status == PlanningSlotStatus.ACTIVE
        assert restored.updated == 1

        again = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert (again.updated, again.skipped) == (0, 1)

    async def test_manual_cancellation_is_not_undone_by_reappearing_event(self, mocks):
        slot, _, _, raw = self._reconcile_setup(mocks, slot_status=PlanningSlotStatus.CANCELLED)
        mocks["connector"].fetch_events.return_value = [raw]
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert slot.status == PlanningSlotStatus.CANCELLED

    async def test_event_moved_outside_window_is_updated_not_cancelled(self, mocks):
        from dataclasses import replace

        slot, instance, _, _ = self._reconcile_setup(mocks)
        moved_start = datetime(2029, 1, 7, 9, tzinfo=UTC)
        moved = replace(
            _raw(start_at=moved_start, end_at=moved_start + timedelta(hours=1)), outside_window=True
        )
        mocks["connector"].fetch_events.return_value = [moved]
        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert result.cancelled == 0
        assert slot.status == PlanningSlotStatus.ACTIVE
        assert instance.actual_start_at == moved_start

    async def test_unknown_event_outside_window_is_not_imported(self, mocks):
        from dataclasses import replace

        mocks["integration_repo"].get.return_value = _integration()
        mocks["link_repo"].get_by_external_event.return_value = None
        mocks["connector"].fetch_events.return_value = [replace(_raw(), outside_window=True)]
        with patch(
            "app.application.sync_service.import_candidate_or_match", AsyncMock(return_value=False)
        ) as ingest:
            result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        ingest.assert_not_awaited()
        assert (result.skipped, result.auto_matched) == (0, 0)

    async def test_plain_uid_containing_separator_is_not_treated_as_occurrence(self, mocks):
        mocks["integration_repo"].get.return_value = _integration()
        mocks["link_repo"].get_by_external_event.return_value = None
        mocks["connector"].fetch_events.return_value = [_raw(uid="urn::legacy::7")]
        with patch(
            "app.application.sync_service.import_candidate_or_match", AsyncMock(return_value=False)
        ):
            await run_sync(_INT_ID, mocks["session"], now=_NOW)
        mocks["link_repo"].get_by_external_event.assert_awaited_once()

    async def test_duplicate_identity_in_one_snapshot_is_processed_once(self, mocks):
        mocks["integration_repo"].get.return_value = _integration()
        mocks["link_repo"].get_by_external_event.return_value = None
        mocks["connector"].fetch_events.return_value = [_raw(), _raw(title="Kollision")]
        with patch(
            "app.application.sync_service.import_candidate_or_match", AsyncMock(return_value=False)
        ) as ingest:
            result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        ingest.assert_awaited_once()
        assert result.failed == 1


class TestCodexReviewFindingsRound2:
    """Regression tests for the second Codex review of PR #483."""

    @pytest.mark.parametrize("edge", ["ends_at_window_start", "starts_at_window_end"])
    async def test_events_touching_half_open_window_bounds_are_not_reconciled(self, mocks, edge):
        mocks["integration_repo"].get.return_value = _integration()
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        window = mocks["connector"].fetch_events.await_args.kwargs
        if edge == "ends_at_window_start":
            start, end = window["from_dt"] - timedelta(hours=1), window["from_dt"]
        else:
            start, end = window["to_dt"], window["to_dt"] + timedelta(hours=1)
        slot = _make_slot()
        instance = _make_event_instance(
            planning_slot_id=slot.id, actual_start_at=start, actual_end_at=end
        )
        mocks["connector"].authoritative_snapshot = True
        mocks["link_repo"].list_active_by_integration.return_value = [
            _make_link(event_instance_id=instance.id)
        ]
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert result.cancelled == 0
        assert slot.status == PlanningSlotStatus.ACTIVE

    async def test_incomplete_snapshot_status_survives_event_failures(self, mocks):
        integration = _integration()
        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].authoritative_snapshot = True
        mocks["connector"].snapshot_complete = False
        mocks["link_repo"].get_by_external_event.return_value = None
        mocks["connector"].fetch_events.return_value = [_raw(), _raw(title="Kollision")]
        with patch(
            "app.application.sync_service.import_candidate_or_match", AsyncMock(return_value=False)
        ):
            result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert result.failed == 1
        assert integration.last_sync_error == (
            "1 calendar event(s) failed during partial sync; "
            "Kalender unvollständig geladen; Löschabgleich übersprungen"
        )

    async def test_provider_cancellation_after_snapshot_gap_is_not_undone(self, mocks):
        from dataclasses import replace

        slot = _make_slot()
        start = _NOW + timedelta(days=30)
        instance = _make_event_instance(
            planning_slot_id=slot.id, actual_start_at=start, actual_end_at=start + timedelta(hours=1)
        )
        raw = _raw(start_at=start, end_at=start + timedelta(hours=1))
        link = _make_link(event_instance_id=instance.id, last_synced_hash=raw.content_hash)
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].authoritative_snapshot = True
        mocks["link_repo"].list_active_by_integration.return_value = [link]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot

        mocks["connector"].fetch_events.return_value = []
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert link.deletion_reason == "missing-from-authoritative-snapshot"

        cancelled = _raw(start_at=start, end_at=start + timedelta(hours=1), is_cancelled=True)
        mocks["connector"].fetch_events.return_value = [cancelled]
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert link.deletion_reason == "provider-cancellation"

        mocks["connector"].fetch_events.return_value = [replace(raw, title="Wieder da")]
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert slot.status == PlanningSlotStatus.CANCELLED


class TestWindowBoundedProvider:
    """CalDAV omits resources moved outside the window; only a confirmed 404 deletes."""

    def _setup(self, mocks, *, resource_id="/cal/gd.ics"):
        slot = _make_slot()
        start = _NOW + timedelta(days=30)
        instance = _make_event_instance(
            planning_slot_id=slot.id, actual_start_at=start, actual_end_at=start + timedelta(hours=1)
        )
        link = _make_link(event_instance_id=instance.id)
        link.provider_resource_id = resource_id
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].authoritative_snapshot = True
        mocks["connector"].window_bounded_snapshot = True
        mocks["connector"].resource_exists = AsyncMock(return_value=True)
        mocks["link_repo"].list_active_by_integration.return_value = [link]
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        return slot

    async def test_resource_moved_outside_window_is_not_cancelled(self, mocks):
        slot = self._setup(mocks)
        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert (result.cancelled, slot.status) == (0, PlanningSlotStatus.ACTIVE)
        mocks["connector"].resource_exists.assert_awaited_once()

    async def test_published_deleted_resource_survives_hard_delete_setting(self, mocks):
        from app.domain.models.calendar_integration import SyncDeleteMode
        from app.domain.models.planning_slot import EventApprovalStatus

        slot = self._setup(mocks)
        slot.approval_status = EventApprovalStatus.CONFIRMED
        slot.released_at = datetime.now(UTC)
        mocks["integration_repo"].get.return_value.delete_behavior = SyncDeleteMode.HARD_DELETE
        mocks["connector"].resource_exists.return_value = False
        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert result.cancelled == 1
        assert slot.status == PlanningSlotStatus.CANCELLED
        mocks["slot_repo"].delete.assert_not_awaited()

    async def test_deleted_resource_is_cancelled(self, mocks):
        slot = self._setup(mocks)
        mocks["connector"].resource_exists.return_value = False
        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert (result.cancelled, slot.status) == (1, PlanningSlotStatus.CANCELLED)

    @pytest.mark.parametrize("failure", ["error", "no_href"])
    async def test_unconfirmed_absence_never_deletes(self, mocks, failure):
        from app.domain.ports.calendar import CalendarConnectorError

        slot = self._setup(mocks, resource_id=None if failure == "no_href" else "/cal/gd.ics")
        mocks["connector"].resource_exists.side_effect = CalendarConnectorError("down")
        result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert (result.cancelled, slot.status) == (0, PlanningSlotStatus.ACTIVE)

    async def test_missing_occurrence_of_returned_resource_is_cancelled_without_check(self, mocks):
        from dataclasses import replace

        slot = self._setup(mocks)
        sibling = replace(_occurrence("20260601T090000Z"), resource_id="/cal/gd.ics")
        mocks["connector"].fetch_events.return_value = [sibling]
        mocks["link_repo"].get_by_external_event.return_value = None
        with patch(
            "app.application.sync_service.import_candidate_or_match", AsyncMock(return_value=False)
        ):
            result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert (result.cancelled, slot.status) == (1, PlanningSlotStatus.CANCELLED)
        mocks["connector"].resource_exists.assert_not_awaited()


class TestCodexReviewFindingsRound4:
    async def test_gap_cancellation_confirmed_by_planner_is_not_undone(self, mocks):
        slot = _make_slot()
        start = _NOW + timedelta(days=30)
        instance = _make_event_instance(
            planning_slot_id=slot.id, actual_start_at=start, actual_end_at=start + timedelta(hours=1)
        )
        raw = _raw(start_at=start, end_at=start + timedelta(hours=1))
        link = _make_link(event_instance_id=instance.id, last_synced_hash=raw.content_hash)
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].authoritative_snapshot = True
        mocks["link_repo"].list_active_by_integration.return_value = [link]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot

        mocks["connector"].fetch_events.return_value = []
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert slot.status == PlanningSlotStatus.CANCELLED

        instance.sync_state = SyncState.DIRTY_INTERNAL  # planner saves the cancellation
        mocks["connector"].fetch_events.return_value = [raw]
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert slot.status == PlanningSlotStatus.CANCELLED

    async def test_moved_override_adopts_legacy_series_link_by_recurrence_id(self, mocks):
        slot = _make_slot()
        instance = _make_event_instance(planning_slot_id=slot.id)
        legacy = _make_link(event_instance_id=instance.id, uid="uid@test", last_synced_hash="old")
        moved = _occurrence(
            _START.strftime("%Y%m%dT%H%M%SZ"),
            start_at=_START + timedelta(hours=2),
            end_at=_END + timedelta(hours=2),
        )

        async def by_external_event(*, provider, external_event_id, calendar_integration_id):
            return legacy if external_event_id == legacy.external_event_id else None

        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [moved]
        mocks["link_repo"].get_by_external_event.side_effect = by_external_event
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot
        await run_sync(_INT_ID, mocks["session"], now=_NOW)
        assert legacy.external_event_id == moved.uid


async def test_incomplete_snapshot_skips_deletion_reconciliation(mocks):
    """Codex 0d600122: a resource that failed to load is not a provider deletion."""
    slot = _make_slot()
    start = _NOW + timedelta(days=30)
    instance = _make_event_instance(
        planning_slot_id=slot.id, actual_start_at=start, actual_end_at=start + timedelta(hours=1)
    )
    integration = _integration()
    mocks["integration_repo"].get.return_value = integration
    mocks["connector"].authoritative_snapshot = True
    mocks["connector"].snapshot_complete = False
    mocks["link_repo"].list_active_by_integration.return_value = [
        _make_link(event_instance_id=instance.id)
    ]
    mocks["instance_repo"].get.return_value = instance
    mocks["slot_repo"].get.return_value = slot
    result = await run_sync(_INT_ID, mocks["session"], now=_NOW)
    assert result.cancelled == 0
    assert slot.status == PlanningSlotStatus.ACTIVE
    assert integration.last_sync_error == (
        "Kalender unvollständig geladen; Löschabgleich übersprungen"
    )


class TestUnsupportedProviders:
    """#467: Google/Microsoft are not supported in 1.0 (no OAuth refresh)."""

    @pytest.mark.parametrize("cal_type", [CalendarType.GOOGLE, CalendarType.MICROSOFT])
    async def test_run_sync_refuses_unsupported_type_without_calling_connector(
        self, mocks, cal_type
    ):
        from app.domain.errors import UnsupportedCalendarTypeError

        integration = _integration()
        integration.type = cal_type
        mocks["integration_repo"].get.return_value = integration
        with pytest.raises(UnsupportedCalendarTypeError, match="ICS"):
            await run_sync(_INT_ID, mocks["session"])
        mocks["connector"].fetch_events.assert_not_called()
