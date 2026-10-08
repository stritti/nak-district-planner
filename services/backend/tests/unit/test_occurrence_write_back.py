"""Occurrences of recurring series must never be written back (Codex 0d600122).

Links store only the composed occurrence key, so push paths rebuild events
without ``recurrence_id``; the guard must recognize the key itself and stop
before any connector call.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import app.application.sync_service as sync_service
from app.adapters.api.routers import events
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.raw_calendar_event import is_occurrence_key, occurrence_key
from app.domain.ports.calendar import OccurrenceWriteBackError

_NOW = datetime(2026, 3, 6, 12, tzinfo=UTC)
_START = datetime(2026, 3, 29, 8, tzinfo=UTC)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (occurrence_key("gd@example", "20260329T080000Z"), True),
        (occurrence_key("gd@example", "20260418"), True),
        (occurrence_key("x" * 600, "20260329T080000Z"), True),
        ("gd@example", False),
        ("urn::legacy::7", False),
    ],
)
def test_occurrence_keys_are_recognized(key, expected):
    assert is_occurrence_key(key) is expected


def _setup(monkeypatch, external_event_id: str):
    integration = CalendarIntegration(
        id=uuid.uuid4(), district_id=uuid.uuid4(), congregation_id=None, name="CalDAV",
        type=CalendarType.CALDAV, credentials_enc="enc", sync_interval=60,
        capabilities=[CalendarCapability.READ, CalendarCapability.WRITE], is_active=True,
        last_synced_at=None, created_at=_NOW, updated_at=_NOW,
    )
    instance = EventInstance.create(
        planning_slot_id=uuid.uuid4(), title="Gottesdienst", actual_start_at=_START,
        actual_end_at=_START + timedelta(minutes=90), source=EventSource.EXTERNAL,
        visibility=EventVisibility.PUBLIC,
    )
    instance.sync_state = SyncState.DIRTY_INTERNAL
    link = ExternalEventLink.create(
        event_instance_id=instance.id, provider="CALDAV", external_event_id=external_event_id,
        calendar_integration_id=integration.id, last_synced_payload={
            "title": "Gottesdienst", "description": None,
            "actual_start_at": (_START - timedelta(hours=1)).isoformat(),
            "actual_end_at": (_START + timedelta(minutes=30)).isoformat(),
        },
        provider_resource_id="/calendars/gemeinde/gd.ics",
    )
    link_repo = AsyncMock()
    link_repo.list_by_event_instance.return_value = [link]
    integration_repo = AsyncMock()
    integration_repo.get.return_value = integration
    connector = MagicMock(update_event_times=AsyncMock(return_value="etag"))
    monkeypatch.setattr(sync_service, "SqlExternalEventLinkRepository", lambda _: link_repo)
    monkeypatch.setattr(sync_service, "SqlCalendarIntegrationRepository", lambda _: integration_repo)
    monkeypatch.setattr(sync_service, "SqlEventInstanceRepository", lambda _: AsyncMock())
    monkeypatch.setattr(sync_service, "_get_connector", lambda _: connector)
    monkeypatch.setattr(sync_service, "decrypt_credentials", lambda _: {"url": "https://dav"})
    return instance, connector


@pytest.mark.parametrize("push", ["push_deviation_resolution", "push_conflict_resolution"])
async def test_push_refuses_occurrence_before_connector_call(monkeypatch, push):
    instance, connector = _setup(monkeypatch, occurrence_key("gd@example", "20260329T080000Z"))
    with pytest.raises(OccurrenceWriteBackError):
        await getattr(sync_service, push)(instance, AsyncMock(spec=AsyncSession))
    connector.update_event_times.assert_not_awaited()


@pytest.mark.parametrize("push", ["push_deviation_resolution", "push_conflict_resolution"])
async def test_push_still_writes_single_events(monkeypatch, push):
    instance, connector = _setup(monkeypatch, "einzeltermin@example")
    assert await getattr(sync_service, push)(instance, AsyncMock(spec=AsyncSession)) is True
    connector.update_event_times.assert_awaited_once()


def _router_fixture():
    from app.domain.models.planning_slot import PlanningSlot

    slot = PlanningSlot.create(
        district_id=uuid.uuid4(), planning_date=_START.date(), planning_time=_START.time(),
        congregation_id=uuid.uuid4(), category="Gottesdienst", title="Gottesdienst",
    )
    instance = EventInstance.create(
        planning_slot_id=slot.id, title="Gottesdienst", actual_start_at=_START,
        actual_end_at=_START + timedelta(minutes=90), source=EventSource.EXTERNAL,
        visibility=EventVisibility.PUBLIC,
    )
    instance.calendar_integration_id = uuid.uuid4()
    slot_repo, instance_repo = AsyncMock(), AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo.get.return_value = instance
    instance_repo.get_by_planning_slot.return_value = instance
    return slot, instance, slot_repo, instance_repo


async def test_resolve_deviation_maps_occurrence_refusal_to_409():
    slot, instance, slot_repo, instance_repo = _router_fixture()
    instance.deviation_flag = True
    push = AsyncMock(side_effect=OccurrenceWriteBackError())
    with (
        patch.object(events, "require_role_in_district"),
        patch.object(events, "DeviationService") as service,
        patch.object(events, "push_deviation_resolution", push),
        pytest.raises(HTTPException) as exc,
    ):
        service.return_value.resolve_deviation = AsyncMock(return_value=True)
        await events.resolve_event_deviation(
            slot.id, MagicMock(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 409
    assert instance.sync_state == SyncState.DIRTY_INTERNAL


async def test_resolve_conflict_maps_occurrence_refusal_to_409():
    slot, instance, slot_repo, instance_repo = _router_fixture()
    instance.sync_state = SyncState.CONFLICT
    push = AsyncMock(side_effect=OccurrenceWriteBackError())
    with (
        patch.object(events, "require_role_in_district"),
        patch.object(events, "push_conflict_resolution", push),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_conflict(
            slot.id, MagicMock(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 409
    assert instance.sync_state == SyncState.CONFLICT
