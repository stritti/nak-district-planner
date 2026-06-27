"""Unit tests for run_sync() — UC-02 calendar sync (EventInstance/ExternalEventLink).

Repositories, crypto, and the calendar connector are all mocked.
No database or network access is required.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.sync_service import run_sync
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
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent

# ── constants ──────────────────────────────────────────────────────────────────

_NOW = datetime(2026, 3, 6, 12, tzinfo=UTC)
_DISTRICT_ID = uuid.uuid4()
_CONG_ID = uuid.uuid4()
_INT_ID = uuid.uuid4()
_START = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
_END = datetime(2026, 4, 10, 10, 0, tzinfo=UTC)


# ── factories ──────────────────────────────────────────────────────────────────


def _integration(**kw) -> CalendarIntegration:
    return CalendarIntegration(
        id=kw.get("id", _INT_ID),
        district_id=kw.get("district_id", _DISTRICT_ID),
        congregation_id=kw.get("congregation_id", _CONG_ID),
        name="Test Kalender",
        type=CalendarType.ICS,
        credentials_enc="encrypted",
        sync_interval=60,
        capabilities=[CalendarCapability.READ],
        is_active=True,
        last_synced_at=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _raw(
    uid: str = "uid@test",
    title: str = "Gottesdienst",
    description: str = "Beschreibung",
    is_cancelled: bool = False,
) -> RawCalendarEvent:
    return RawCalendarEvent(
        uid=uid,
        title=title,
        start_at=_START,
        end_at=_END,
        description=description,
        content_hash="",
        is_cancelled=is_cancelled,
    )


def _make_event_instance(**kw) -> EventInstance:
    return EventInstance.create(
        planning_slot_id=kw.get("planning_slot_id", uuid.uuid4()),
        title=kw.get("title", "Gottesdienst"),
        actual_start_at=kw.get("actual_start_at", _START),
        actual_end_at=kw.get("actual_end_at", _END),
        source=EventSource.EXTERNAL,
        visibility=EventVisibility.PUBLIC,
        content_hash=kw.get("content_hash"),
        instance_id=kw.get("instance_id"),
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
        category="Gottesdienst",
        title="Gottesdienst",
    )


# ── fixture ────────────────────────────────────────────────────────────────────


@pytest.fixture
def mocks():
    """Patch all sync_service dependencies and return the mock objects."""
    link_repo = AsyncMock()
    instance_repo = AsyncMock()
    slot_repo = AsyncMock()
    integration_repo = AsyncMock()
    connector = MagicMock()
    connector.fetch_events = AsyncMock(return_value=[])
    compute_hash = MagicMock(return_value="hash-current")

    patchers = [
        patch(
            "app.application.sync_service.SqlExternalEventLinkRepository",
            return_value=link_repo,
        ),
        patch(
            "app.application.sync_service.SqlEventInstanceRepository",
            return_value=instance_repo,
        ),
        patch(
            "app.application.sync_service.SqlPlanningSlotRepository",
            return_value=slot_repo,
        ),
        patch(
            "app.application.sync_service.SqlCalendarIntegrationRepository",
            return_value=integration_repo,
        ),
        patch("app.application.sync_service._get_connector", return_value=connector),
        patch(
            "app.application.sync_service.decrypt_credentials",
            MagicMock(return_value={"url": "https://example.com/cal.ics"}),
        ),
        patch("app.application.sync_service._compute_content_hash", compute_hash),
    ]

    for p in patchers:
        p.start()

    # Prevent auto-matching by default (no existing planning slots to match)
    slot_repo.list_for_date_range = AsyncMock(return_value=[])

    yield {
        "link_repo": link_repo,
        "instance_repo": instance_repo,
        "slot_repo": slot_repo,
        "integration_repo": integration_repo,
        "connector": connector,
        "compute_hash": compute_hash,
        "session": AsyncMock(spec=AsyncSession),
    }

    for p in patchers:
        p.stop()


# ── tests ──────────────────────────────────────────────────────────────────────


class TestRunSync:
    """Test suite for run_sync() with mocked repositories and connector."""

    async def test_integration_not_found_raises(self, mocks):
        """Integration lookup returns None → ValueError."""
        mocks["integration_repo"].get.return_value = None

        with pytest.raises(ValueError, match=str(_INT_ID)):
            await run_sync(_INT_ID, mocks["session"])

        mocks["integration_repo"].get.assert_awaited_once_with(_INT_ID)

    async def test_new_event_creates_planning_slot_and_instance(self, mocks):
        """No existing link → PlanningSlot + EventInstance + ExternalEventLink created."""
        integration = _integration()
        raw = _raw()

        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = None

        result = await run_sync(_INT_ID, mocks["session"])

        assert result == {"created": 1, "updated": 0, "cancelled": 0, "auto_matched": 0}

        mocks["link_repo"].get_by_external_event.assert_awaited_once_with(
            provider=CalendarType.ICS.value,
            external_event_id=raw.uid,
            calendar_integration_id=_INT_ID,
        )
        mocks["slot_repo"].save.assert_awaited_once()
        mocks["instance_repo"].save.assert_awaited_once()
        mocks["link_repo"].save.assert_awaited_once()

        saved_slot = mocks["slot_repo"].save.call_args[0][0]
        assert saved_slot.district_id == _DISTRICT_ID
        assert saved_slot.congregation_id == _CONG_ID

        saved_instance = mocks["instance_repo"].save.call_args[0][0]
        assert saved_instance.source == EventSource.EXTERNAL
        assert saved_instance.external_uid == raw.uid

        saved_link = mocks["link_repo"].save.call_args[0][0]
        assert saved_link.provider == CalendarType.ICS.value
        assert saved_link.external_event_id == raw.uid

    async def test_new_cancelled_event_skipped(self, mocks):
        """No existing link + raw.is_cancelled → silently skipped."""
        mocks["integration_repo"].get.return_value = _integration()
        mocks["connector"].fetch_events.return_value = [_raw(is_cancelled=True)]
        mocks["link_repo"].get_by_external_event.return_value = None

        result = await run_sync(_INT_ID, mocks["session"])

        assert result == {"created": 0, "updated": 0, "cancelled": 0, "auto_matched": 0}
        mocks["link_repo"].get_by_external_event.assert_awaited_once()
        mocks["slot_repo"].save.assert_not_called()
        mocks["instance_repo"].save.assert_not_called()
        mocks["link_repo"].save.assert_not_called()

    async def test_changed_event_updates_instance(self, mocks):
        """Existing link with mismatched hash → EventInstance + link updated."""
        integration = _integration()
        instance = _make_event_instance(content_hash="old-hash")
        link = _make_link(
            event_instance_id=instance.id,
            uid="uid@test",
            last_synced_hash="old-hash",
        )
        raw = _raw(title="Neuer Titel")

        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["compute_hash"].return_value = "new-hash"

        result = await run_sync(_INT_ID, mocks["session"])

        assert result == {"created": 0, "updated": 1, "cancelled": 0, "auto_matched": 0}

        mocks["link_repo"].get_by_external_event.assert_awaited_once_with(
            provider=CalendarType.ICS.value,
            external_event_id=raw.uid,
            calendar_integration_id=_INT_ID,
        )
        mocks["instance_repo"].get.assert_awaited_once_with(link.event_instance_id)

        # Instance mutated in-place
        assert instance.title == "Neuer Titel"
        assert instance.content_hash == "new-hash"
        assert instance.sync_state == SyncState.DIRTY_EXTERNAL
        mocks["instance_repo"].save.assert_awaited_once_with(instance)

        # Link hash updated
        assert link.last_synced_hash == "new-hash"
        mocks["link_repo"].save.assert_awaited_once_with(link)

    async def test_unchanged_event_skipped(self, mocks):
        """Existing link with matching hash → nothing saved."""
        integration = _integration()
        instance = _make_event_instance()
        link = _make_link(
            event_instance_id=instance.id,
            uid="uid@test",
            last_synced_hash="same-hash",
        )
        raw = _raw()

        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["compute_hash"].return_value = "same-hash"

        result = await run_sync(_INT_ID, mocks["session"])

        assert result == {"created": 0, "updated": 0, "cancelled": 0, "auto_matched": 0}
        mocks["instance_repo"].save.assert_not_called()
        mocks["link_repo"].save.assert_not_called()
        mocks["slot_repo"].save.assert_not_called()

    async def test_existing_cancelled_event_cancels_slot(self, mocks):
        """Existing link + raw.is_cancelled → slot status CANCELLED, instance DIRTY_EXTERNAL."""
        integration = _integration()
        slot = _make_slot(congregation_id=_CONG_ID)
        instance = _make_event_instance(planning_slot_id=slot.id)
        link = _make_link(event_instance_id=instance.id, uid="uid@test")
        raw = _raw(is_cancelled=True)

        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = link
        mocks["instance_repo"].get.return_value = instance
        mocks["slot_repo"].get.return_value = slot

        result = await run_sync(_INT_ID, mocks["session"])

        assert result == {"created": 0, "updated": 0, "cancelled": 1, "auto_matched": 0}

        mocks["link_repo"].get_by_external_event.assert_awaited_once_with(
            provider=CalendarType.ICS.value,
            external_event_id=raw.uid,
            calendar_integration_id=_INT_ID,
        )
        mocks["instance_repo"].get.assert_awaited_once_with(link.event_instance_id)
        mocks["slot_repo"].get.assert_awaited_once_with(instance.planning_slot_id)

        assert slot.status == PlanningSlotStatus.CANCELLED
        mocks["slot_repo"].save.assert_awaited_once_with(slot)

        assert instance.sync_state == SyncState.DIRTY_EXTERNAL
        mocks["instance_repo"].save.assert_awaited_once_with(instance)

    async def test_last_synced_at_updated(self, mocks):
        """Empty fetch still updates integration.last_synced_at."""
        integration = _integration()
        assert integration.last_synced_at is None

        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = []

        await run_sync(_INT_ID, mocks["session"])

        assert integration.last_synced_at is not None
        mocks["integration_repo"].save.assert_awaited_once_with(integration)

    async def test_counts_returned_correctly(self, mocks):
        """Mixed new / changed / cancelled / unchanged events → correct counters."""
        integration = _integration()

        raw_new = _raw(uid="new@test", title="New Event")
        raw_changed = _raw(uid="changed@test", title="Changed Event")
        raw_cancelled = _raw(
            uid="cancelled@test", title="Cancelled Event", is_cancelled=True
        )
        raw_unchanged = _raw(uid="unchanged@test", title="Unchanged Event")

        # Existing entities for the events that have a link
        instance_changed = _make_event_instance()
        link_changed = _make_link(
            event_instance_id=instance_changed.id,
            uid="changed@test",
            last_synced_hash="old-hash",
        )

        instance_cancelled = _make_event_instance()
        link_cancelled = _make_link(
            event_instance_id=instance_cancelled.id,
            uid="cancelled@test",
        )
        slot_cancelled = _make_slot(congregation_id=_CONG_ID)

        instance_unchanged = _make_event_instance()
        link_unchanged = _make_link(
            event_instance_id=instance_unchanged.id,
            uid="unchanged@test",
            last_synced_hash="same-hash",
        )

        # Link lookup based on external_event_id
        link_map: dict[str, object] = {
            "new@test": None,
            "changed@test": link_changed,
            "cancelled@test": link_cancelled,
            "unchanged@test": link_unchanged,
        }
        mocks["link_repo"].get_by_external_event.side_effect = (
            lambda provider, external_event_id, calendar_integration_id: link_map.get(
                external_event_id
            )
        )

        # Instance lookup by id
        instance_map = {
            instance_changed.id: instance_changed,
            instance_cancelled.id: instance_cancelled,
            instance_unchanged.id: instance_unchanged,
        }
        mocks["instance_repo"].get.side_effect = (
            lambda instance_id: instance_map.get(instance_id)
        )

        mocks["slot_repo"].get.return_value = slot_cancelled

        # Hash control: make raw_changed differ and raw_unchanged match
        def _hash_side_effect(raw):
            return {
                "new@test": "hash-new",
                "changed@test": "new-hash",  # differs from link_changed's "old-hash"
                "cancelled@test": "hash-cancelled",
                "unchanged@test": "same-hash",  # matches link_unchanged's "same-hash"
            }.get(raw.uid, "unknown")

        mocks["compute_hash"].side_effect = _hash_side_effect

        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [
            raw_new,
            raw_changed,
            raw_cancelled,
            raw_unchanged,
        ]

        result = await run_sync(_INT_ID, mocks["session"])

        assert result == {
            "created": 1,
            "updated": 1,
            "cancelled": 1,
            "auto_matched": 0,
        }

    async def test_congregation_id_propagated(self, mocks):
        """New event inherits congregation_id from the integration."""
        cong_id = uuid.uuid4()
        integration = _integration(congregation_id=cong_id)
        raw = _raw()

        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = None

        await run_sync(_INT_ID, mocks["session"])

        saved_slot = mocks["slot_repo"].save.call_args[0][0]
        assert saved_slot.congregation_id == cong_id

    async def test_district_level_integration(self, mocks):
        """Integration without congregation_id → slot.congregation_id is None."""
        integration = _integration(congregation_id=None)
        raw = _raw()

        mocks["integration_repo"].get.return_value = integration
        mocks["connector"].fetch_events.return_value = [raw]
        mocks["link_repo"].get_by_external_event.return_value = None

        await run_sync(_INT_ID, mocks["session"])

        saved_slot = mocks["slot_repo"].save.call_args[0][0]
        assert saved_slot.congregation_id is None
