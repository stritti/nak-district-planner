from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.application.planning_model_bridge import event_instance_from_event, planning_slot_from_event
from app.domain.models.event import Event, EventSource, EventStatus, EventVisibility
from app.domain.models.planning_slot import PlanningSlotStatus
from app.domain.models.service_assignment import ServiceAssignment


def _sample_event(*, status: EventStatus = EventStatus.DRAFT) -> Event:
    event_id = uuid.uuid4()
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    start_at = datetime(2026, 4, 12, 9, 30, tzinfo=timezone.utc)
    end_at = datetime(2026, 4, 12, 11, 0, tzinfo=timezone.utc)
    now = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    return Event(
        id=event_id,
        title="Gottesdienst",
        description="Sonntagmorgen",
        start_at=start_at,
        end_at=end_at,
        district_id=district_id,
        congregation_id=congregation_id,
        category="Gottesdienst",
        source=EventSource.INTERNAL,
        status=status,
        visibility=EventVisibility.INTERNAL,
        audiences=[],
        applicability=[],
        external_uid=None,
        calendar_integration_id=None,
        content_hash=None,
        created_at=now,
        updated_at=now,
    )


def test_planning_slot_from_event_uses_legacy_event_id_for_bridge() -> None:
    event = _sample_event()

    slot = planning_slot_from_event(event)

    assert slot.id == event.id
    assert slot.district_id == event.district_id
    assert slot.congregation_id == event.congregation_id
    assert slot.planning_date == event.start_at.date()
    assert slot.planning_time == event.start_at.timetz().replace(tzinfo=None)
    assert slot.status == PlanningSlotStatus.ACTIVE


def test_planning_slot_from_cancelled_event_marks_slot_cancelled() -> None:
    event = _sample_event(status=EventStatus.CANCELLED)

    slot = planning_slot_from_event(event)

    assert slot.status == PlanningSlotStatus.CANCELLED


def test_event_instance_from_event_keeps_actual_execution_fields() -> None:
    event = _sample_event()

    instance = event_instance_from_event(event)

    assert instance.id == event.id
    assert instance.planning_slot_id == event.id
    assert instance.actual_start_at == event.start_at
    assert instance.actual_end_at == event.end_at
    assert instance.deviation_flag is False


def test_service_assignment_defaults_planning_slot_to_event_bridge_id() -> None:
    event = _sample_event()

    assignment = ServiceAssignment.create(event_id=event.id, leader_name="Bruder Beispiel")

    assert assignment.event_id == event.id
    assert assignment.planning_slot_id == event.id
