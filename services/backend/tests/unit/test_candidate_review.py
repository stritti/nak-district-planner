from datetime import UTC, datetime, time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.application.candidate_review import CandidateReviewService
from app.domain.errors import (
    CandidateAlreadyReviewedError,
    CandidateSlotAlreadyLinkedError,
    CandidateSlotNotAssignableError,
)
from app.domain.models.calendar_integration import CalendarIntegration, CalendarType
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_candidate import CandidateStatus, ExternalEventCandidate
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent


def candidate() -> ExternalEventCandidate:
    integration = CalendarIntegration.create(
        district_id=uuid4(),
        name="Test",
        type=CalendarType.ICS,
        credentials_enc="encrypted",
    )
    raw = RawCalendarEvent(
        uid="external-id",
        title="Auswärtiger Termin",
        start_at=datetime(2026, 6, 1, 10, tzinfo=UTC),
        end_at=datetime(2026, 6, 1, 11, tzinfo=UTC),
        description="Details",
        content_hash="provider-hash",
        is_cancelled=False,
    )
    return ExternalEventCandidate.create(
        integration=integration,
        raw=raw,
        content_hash="content-hash",
    )


def service() -> CandidateReviewService:
    return CandidateReviewService(
        candidates=AsyncMock(),
        slots=AsyncMock(),
        instances=AsyncMock(),
        links=AsyncMock(),
    )


async def test_accept_creates_slot_instance_and_link():
    item, review = candidate(), service()
    review.instances.get_by_planning_slot.return_value = None

    accepted = await review.accept(item, user_sub="admin")

    created_slot = review.slots.save.call_args.args[0]
    created_instance = review.instances.save.call_args.args[0]
    link = review.links.save.call_args.args[0]
    assert accepted.status == CandidateStatus.ACCEPTED
    assert accepted.matched_slot_id == created_slot.id
    assert created_slot.district_id == item.district_id
    assert created_slot.planning_time == time(10)
    assert created_instance.external_uid == item.external_event_id
    assert created_instance.sync_state == SyncState.CLEAN
    assert link.calendar_integration_id == item.calendar_integration_id


async def test_accept_existing_slot_requires_same_district_and_active_state():
    item, review = candidate(), service()
    foreign_slot = PlanningSlot.create(
        district_id=uuid4(),
        planning_date=item.event_date,
        planning_time=item.event_time,
    )
    review.slots.get.return_value = foreign_slot

    with pytest.raises(CandidateSlotNotAssignableError):
        await review.accept(item, user_sub="admin", slot_id=foreign_slot.id)

    foreign_slot.district_id = item.district_id
    foreign_slot.status = PlanningSlotStatus.CANCELLED
    with pytest.raises(CandidateSlotNotAssignableError):
        await review.accept(item, user_sub="admin", slot_id=foreign_slot.id)


async def test_accept_refuses_duplicate_or_dirty_linked_slot():
    item, review = candidate(), service()
    slot = PlanningSlot.create(
        district_id=item.district_id,
        planning_date=item.event_date,
        planning_time=item.event_time,
    )
    review.slots.get.return_value = slot
    linked = EventInstance.create(
        planning_slot_id=slot.id,
        title="Existing",
        actual_start_at=item.start_at,
        actual_end_at=item.end_at,
        source=EventSource.EXTERNAL,
        visibility=EventVisibility.PUBLIC,
        calendar_integration_id=uuid4(),
    )
    review.instances.get_by_planning_slot.return_value = linked

    with pytest.raises(CandidateSlotAlreadyLinkedError):
        await review.accept(item, user_sub="admin", slot_id=slot.id)

    linked.calendar_integration_id = None
    linked.sync_state = SyncState.DIRTY_INTERNAL
    with pytest.raises(CandidateSlotAlreadyLinkedError):
        await review.accept(item, user_sub="admin", slot_id=slot.id)


async def test_review_state_is_terminal_and_dismiss_records_actor():
    item, review = candidate(), service()

    dismissed = await review.dismiss(item, user_sub="admin")

    assert dismissed.status == CandidateStatus.DISMISSED
    assert dismissed.reviewed_by == "admin"
    with pytest.raises(CandidateAlreadyReviewedError):
        await review.accept(item, user_sub="admin")


def test_refresh_updates_data_without_implicit_status_transition():
    item = candidate()
    changed = RawCalendarEvent(
        uid=item.external_event_id,
        title="Geändert",
        start_at=item.start_at,
        end_at=item.end_at,
        description="Neu",
        content_hash="ignored",
        is_cancelled=True,
    )

    item.refresh(changed, "changed", "Kategorie")

    assert item.status == CandidateStatus.PENDING
    assert item.title == "Geändert"
    assert item.content_hash == "changed"
