"""Regression coverage for the new-event governance boundary."""

from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.application.external_candidate_ingestion import (
    find_exact_matching_slot,
    ingest_unlinked_event,
)
from app.domain.models.calendar_integration import CalendarIntegration, CalendarType
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_candidate import CandidateStatus, ExternalEventCandidate
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent

START = datetime(2026, 7, 1, 10, tzinfo=UTC)


def integration():
    return CalendarIntegration.create(
        district_id=uuid4(), name="External", type=CalendarType.ICS,
        credentials_enc="encrypted", congregation_id=uuid4(),
    )


def event(*, uid="ext", cancelled=False):
    return RawCalendarEvent(
        uid=uid, title="Meeting", start_at=START,
        end_at=START + timedelta(hours=1), description="Description",
        content_hash="provider", is_cancelled=cancelled,
        revision_marker="etag", resource_id="resource-id",
    )


def repos():
    return dict(
        candidate_repo=AsyncMock(), instance_repo=AsyncMock(),
        link_repo=AsyncMock(), notification_repo=AsyncMock(),
    )


async def test_unmatched_event_becomes_candidate_without_unapproved_slot():
    config, adapters = integration(), repos()
    adapters["candidate_repo"].by_external_event.return_value = None
    with patch("app.application.external_candidate_ingestion.find_exact_matching_slot", return_value=None):
        result = await ingest_unlinked_event(
            raw=event(), integration=config, session=AsyncMock(),
            content_hash="hash", **adapters,
        )
    assert result is False
    item = adapters["candidate_repo"].save.call_args.args[0]
    assert item.status == CandidateStatus.PENDING
    assert item.external_event_id == "ext"
    adapters["instance_repo"].save.assert_not_awaited()
    adapters["link_repo"].save.assert_not_awaited()
    adapters["notification_repo"].save.assert_awaited_once()


@pytest.mark.parametrize("slot_category", [None, "Gottesdienst"])
async def test_exact_match_handles_categoryless_integration(slot_category):
    config = integration()
    assert config.default_category is None
    slot = PlanningSlot.create(
        district_id=config.district_id, congregation_id=config.congregation_id,
        planning_date=START.date(), planning_time=time(10), category=slot_category,
    )
    with patch("app.application.external_candidate_ingestion.SqlPlanningSlotRepository") as repository:
        repository.return_value.list_for_date_range = AsyncMock(return_value=[slot])
        assert await find_exact_matching_slot(
            session=AsyncMock(), district_id=config.district_id,
            congregation_id=config.congregation_id, event_start=START,
            event_category=config.default_category,
        ) == slot


async def test_matching_occupied_slot_creates_candidate_and_never_overwrites_mapping():
    config, adapters = integration(), repos()
    slot = PlanningSlot.create(
        district_id=config.district_id, congregation_id=config.congregation_id,
        planning_date=START.date(), planning_time=time(10),
    )
    instance = EventInstance.create(
        planning_slot_id=slot.id, title="Already linked", actual_start_at=START,
        actual_end_at=START + timedelta(hours=1), source=EventSource.EXTERNAL,
        visibility=EventVisibility.PUBLIC, calendar_integration_id=uuid4(),
    )
    adapters["instance_repo"].get_by_planning_slot.return_value = instance
    adapters["candidate_repo"].by_external_event.return_value = None
    with patch("app.application.external_candidate_ingestion.find_exact_matching_slot", return_value=slot):
        result = await ingest_unlinked_event(
            raw=event(), integration=config, session=AsyncMock(),
            content_hash="hash", **adapters,
        )
    assert result is False
    adapters["instance_repo"].save.assert_not_awaited()
    adapters["link_repo"].save.assert_not_awaited()
    adapters["candidate_repo"].save.assert_awaited_once()


async def test_matching_unlinked_slot_preserves_provider_baseline():
    config, adapters = integration(), repos()
    slot = PlanningSlot.create(
        district_id=config.district_id, congregation_id=config.congregation_id,
        planning_date=START.date(), planning_time=time(10),
    )
    adapters["candidate_repo"].by_external_event.return_value = None
    adapters["instance_repo"].get_by_planning_slot.return_value = None
    with patch("app.application.external_candidate_ingestion.find_exact_matching_slot", return_value=slot):
        result = await ingest_unlinked_event(
            raw=event(), integration=config, session=AsyncMock(),
            content_hash="hash", **adapters,
        )
    assert result is True
    link = adapters["link_repo"].save.call_args.args[0]
    assert link.revision_marker == "etag"
    assert link.provider_resource_id == "resource-id"
    assert link.last_synced_payload["description"] == "Description"
    adapters["notification_repo"].save.assert_not_awaited()


async def test_pending_candidate_is_accepted_after_later_exact_match():
    config, adapters = integration(), repos()
    raw = event()
    candidate = ExternalEventCandidate.create(integration=config, raw=raw, content_hash="old")
    adapters["candidate_repo"].by_external_event.return_value = candidate
    adapters["instance_repo"].get_by_planning_slot.return_value = None
    slot = PlanningSlot.create(
        district_id=config.district_id, congregation_id=config.congregation_id,
        planning_date=START.date(), planning_time=time(10),
    )
    with patch("app.application.external_candidate_ingestion.find_exact_matching_slot", return_value=slot):
        result = await ingest_unlinked_event(
            raw=raw, integration=config, session=AsyncMock(),
            content_hash="new", **adapters,
        )
    assert result is True
    assert candidate.status == CandidateStatus.ACCEPTED
    assert candidate.matched_slot_id == slot.id
    adapters["notification_repo"].save.assert_not_awaited()


async def test_cancelled_candidate_becomes_dismissed():
    config, adapters = integration(), repos()
    raw = event(cancelled=True)
    candidate = ExternalEventCandidate.create(integration=config, raw=raw, content_hash="old")
    adapters["candidate_repo"].by_external_event.return_value = candidate
    result = await ingest_unlinked_event(
        raw=raw, integration=config, session=AsyncMock(),
        content_hash="new", **adapters,
    )
    assert result is False
    assert candidate.status == CandidateStatus.DISMISSED
    adapters["link_repo"].save.assert_not_awaited()


async def test_invalid_interval_does_not_persist_candidate():
    config, adapters = integration(), repos()
    raw = event()
    raw = RawCalendarEvent(
        uid=raw.uid, title=raw.title, start_at=raw.start_at,
        end_at=raw.start_at, description=raw.description,
        content_hash=raw.content_hash, is_cancelled=False,
    )
    adapters["candidate_repo"].by_external_event.return_value = None
    assert await ingest_unlinked_event(
        raw=raw, integration=config, session=AsyncMock(),
        content_hash="hash", **adapters,
    ) is False
    adapters["candidate_repo"].save.assert_not_awaited()
    adapters["instance_repo"].save.assert_not_awaited()
