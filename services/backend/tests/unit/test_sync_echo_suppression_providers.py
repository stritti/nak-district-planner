# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Provider-specific regression tests for calendar sync echo suppression.

Task 4.5 requires more than parametrizing a shared connector mock. These tests
instantiate the real writable connector classes so their provider semantics,
most importantly authoritative snapshot behaviour, participate in the sync
algorithm while network I/O remains mocked.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.application.sync_service as sync_service
from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.google_connector import GoogleCalendarConnector
from app.adapters.calendar.microsoft_connector import MicrosoftGraphCalendarConnector
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_link import ExternalEventLink, ExternalEventLinkState
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.services.sync_policy import INTERNAL_DELETE_MARKER

_NOW = datetime(2026, 3, 6, 12, tzinfo=UTC)
_START = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
_END = datetime(2026, 4, 10, 10, 0, tzinfo=UTC)
_DISTRICT_ID = uuid.uuid4()
_CONG_ID = uuid.uuid4()
_INT_ID = uuid.uuid4()

_CONNECTOR_TYPES = {
    CalendarType.GOOGLE: GoogleCalendarConnector,
    CalendarType.MICROSOFT: MicrosoftGraphCalendarConnector,
    CalendarType.CALDAV: CalDAVConnector,
}


def _hash(
    *,
    start_at: datetime = _START,
    end_at: datetime = _END,
    title: str = "Gottesdienst",
    description: str | None = "Beschreibung",
    cancelled: bool = False,
) -> str:
    raw = RawCalendarEvent(
        uid="uid@test",
        title=title,
        start_at=start_at,
        end_at=end_at,
        description=description,
        content_hash="",
        is_cancelled=cancelled,
    )
    return sync_service._compute_content_hash(raw)


def _raw(
    *,
    start_at: datetime = _START,
    end_at: datetime = _END,
    cancelled: bool = False,
) -> RawCalendarEvent:
    return RawCalendarEvent(
        uid="uid@test",
        title="Gottesdienst",
        start_at=start_at,
        end_at=end_at,
        description="Beschreibung",
        content_hash="",
        is_cancelled=cancelled,
        revision_marker="provider-revision",
        resource_id="provider-resource",
    )


def _integration(provider: CalendarType) -> CalendarIntegration:
    return CalendarIntegration(
        id=_INT_ID,
        district_id=_DISTRICT_ID,
        congregation_id=_CONG_ID,
        name="Provider test",
        type=provider,
        credentials_enc="encrypted",
        sync_interval=60,
        capabilities=[CalendarCapability.READ, CalendarCapability.WRITE],
        is_active=True,
        last_synced_at=None,
        created_at=_NOW,
        updated_at=_NOW,
        last_sync_error=None,
    )


def _slot(*, cancelled: bool = False) -> PlanningSlot:
    slot = PlanningSlot.create(
        district_id=_DISTRICT_ID,
        planning_date=_START.date(),
        planning_time=_START.time(),
        congregation_id=_CONG_ID,
        category="Gottesdienst",
        title="Gottesdienst",
    )
    if cancelled:
        slot.status = PlanningSlotStatus.CANCELLED
    return slot


def _instance(slot: PlanningSlot, *, shifted: bool = False) -> EventInstance:
    instance = EventInstance.create(
        planning_slot_id=slot.id,
        title="Gottesdienst",
        actual_start_at=_START + (timedelta(hours=1) if shifted else timedelta()),
        actual_end_at=_END + (timedelta(hours=1) if shifted else timedelta()),
        source=EventSource.EXTERNAL,
        visibility=EventVisibility.PUBLIC,
    )
    instance.sync_state = SyncState.DIRTY_INTERNAL
    return instance


def _link(instance: EventInstance, provider: CalendarType) -> ExternalEventLink:
    return ExternalEventLink.create(
        event_instance_id=instance.id,
        provider=provider.value,
        external_event_id="uid@test",
        calendar_integration_id=_INT_ID,
        last_synced_hash=_hash(),
        revision_marker="provider-revision",
        provider_resource_id="provider-resource",
    )


def _install_runtime(monkeypatch: pytest.MonkeyPatch, provider: CalendarType):
    # GOOGLE/MICROSOFT are disabled in 1.0 (#467); connectors are kept and stay covered.
    monkeypatch.setattr(
        "app.application.sync_service.SUPPORTED_CALENDAR_TYPES", frozenset(CalendarType)
    )
    connector_cls = _CONNECTOR_TYPES[provider]
    connector = connector_cls(client=MagicMock())
    connector.fetch_events = AsyncMock(return_value=[])
    connector.update_event_times = AsyncMock(return_value="ack-revision")
    connector.delete_event = AsyncMock()

    integration_repo = AsyncMock()
    instance_repo = AsyncMock()
    slot_repo = AsyncMock()
    link_repo = AsyncMock()
    session = AsyncMock(spec=AsyncSession)

    monkeypatch.setattr(sync_service, "_get_connector", lambda calendar_type: connector)
    monkeypatch.setattr(sync_service, "decrypt_credentials", lambda _: {"test": "credentials"})
    monkeypatch.setattr(
        sync_service, "SqlCalendarIntegrationRepository", lambda _: integration_repo
    )
    monkeypatch.setattr(sync_service, "SqlEventInstanceRepository", lambda _: instance_repo)
    monkeypatch.setattr(sync_service, "SqlPlanningSlotRepository", lambda _: slot_repo)
    monkeypatch.setattr(sync_service, "SqlExternalEventLinkRepository", lambda _: link_repo)

    integration_repo.get.return_value = _integration(provider)
    link_repo.list_active_by_integration.return_value = []
    return connector, integration_repo, instance_repo, slot_repo, link_repo, session


@pytest.mark.parametrize(
    "provider",
    [CalendarType.GOOGLE, CalendarType.MICROSOFT, CalendarType.CALDAV],
)
async def test_update_echo_is_write_free_with_real_provider_semantics(
    monkeypatch: pytest.MonkeyPatch, provider: CalendarType
) -> None:
    connector, _, instance_repo, slot_repo, link_repo, session = _install_runtime(
        monkeypatch, provider
    )
    slot = _slot()
    instance = _instance(slot, shifted=True)
    link = _link(instance, provider)
    connector.fetch_events.return_value = [_raw()]
    link_repo.get_by_external_event.return_value = link
    instance_repo.get.return_value = instance
    slot_repo.get.return_value = slot
    link_repo.list_active_by_integration.return_value = [link]

    first = await sync_service.run_sync(_INT_ID, session)
    assert first.updated == 1
    assert instance.sync_state == SyncState.CLEAN
    acknowledged_hash = link.last_synced_hash

    connector.update_event_times.reset_mock()
    instance_repo.save.reset_mock()
    link_repo.save.reset_mock()
    connector.fetch_events.return_value = [
        _raw(start_at=_START + timedelta(hours=1), end_at=_END + timedelta(hours=1))
    ]

    second = await sync_service.run_sync(_INT_ID, session)

    assert second.skipped == 1
    assert second.updated == 0
    connector.update_event_times.assert_not_awaited()
    instance_repo.save.assert_not_awaited()
    link_repo.save.assert_not_awaited()
    assert link.last_synced_hash == acknowledged_hash


async def test_google_delete_echo_uses_explicit_cancellation_tombstone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CalendarType.GOOGLE
    connector, _, instance_repo, slot_repo, link_repo, session = _install_runtime(
        monkeypatch, provider
    )
    assert connector.authoritative_snapshot is False

    slot = _slot(cancelled=True)
    instance = _instance(slot)
    link = _link(instance, provider)
    connector.fetch_events.return_value = [_raw()]
    link_repo.get_by_external_event.return_value = link
    instance_repo.get.return_value = instance
    slot_repo.get.return_value = slot

    first = await sync_service.run_sync(_INT_ID, session)
    assert first.cancelled == 1
    assert link.state == ExternalEventLinkState.SYNC_TOMBSTONE
    assert link.revision_marker == INTERNAL_DELETE_MARKER

    connector.delete_event.reset_mock()
    instance_repo.save.reset_mock()
    slot_repo.save.reset_mock()
    slot_repo.delete.reset_mock()
    link_repo.save.reset_mock()
    connector.fetch_events.return_value = [_raw(cancelled=True)]

    second = await sync_service.run_sync(_INT_ID, session)

    assert second.skipped == 1
    assert second.cancelled == 0
    connector.delete_event.assert_not_awaited()
    instance_repo.save.assert_not_awaited()
    slot_repo.save.assert_not_awaited()
    slot_repo.delete.assert_not_awaited()
    link_repo.save.assert_not_awaited()
    link_repo.list_active_by_integration.assert_not_awaited()


# Microsoft is not an authoritative snapshot (no presence check for moved events).
@pytest.mark.parametrize("provider", [CalendarType.CALDAV])
async def test_collection_provider_delete_echo_uses_missing_resource_reconciliation(
    monkeypatch: pytest.MonkeyPatch, provider: CalendarType
) -> None:
    connector, _, instance_repo, slot_repo, link_repo, session = _install_runtime(
        monkeypatch, provider
    )
    assert connector.authoritative_snapshot is True

    slot = _slot(cancelled=True)
    instance = _instance(slot)
    link = _link(instance, provider)
    connector.fetch_events.return_value = [_raw()]
    link_repo.get_by_external_event.return_value = link
    instance_repo.get.return_value = instance
    slot_repo.get.return_value = slot
    link_repo.list_active_by_integration.return_value = [link]

    first = await sync_service.run_sync(_INT_ID, session)
    assert first.cancelled == 1
    assert link.state == ExternalEventLinkState.SYNC_TOMBSTONE
    assert link.revision_marker == INTERNAL_DELETE_MARKER

    connector.delete_event.reset_mock()
    instance_repo.save.reset_mock()
    slot_repo.save.reset_mock()
    slot_repo.delete.reset_mock()
    link_repo.save.reset_mock()
    link_repo.list_active_by_integration.reset_mock()
    connector.fetch_events.return_value = []
    # Repository contract: durable tombstones are not returned as active links.
    link_repo.list_active_by_integration.return_value = []

    second = await sync_service.run_sync(_INT_ID, session)

    assert second.cancelled == 0
    assert second.failed == 0
    connector.delete_event.assert_not_awaited()
    instance_repo.save.assert_not_awaited()
    slot_repo.save.assert_not_awaited()
    slot_repo.delete.assert_not_awaited()
    link_repo.save.assert_not_awaited()
    link_repo.list_active_by_integration.assert_awaited_once_with(_INT_ID)
