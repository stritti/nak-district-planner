from __future__ import annotations

from app.domain.models.event import Event, EventStatus
from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus


def planning_slot_from_event(event: Event) -> PlanningSlot:
    return PlanningSlot(
        id=event.id,
        district_id=event.district_id,
        series_id=None,
        congregation_id=event.congregation_id,
        category=event.category,
        planning_date=event.start_at.date(),
        planning_time=event.start_at.timetz().replace(tzinfo=None),
        status=_planning_slot_status(event.status),
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def event_instance_from_event(event: Event) -> EventInstance:
    return EventInstance(
        id=event.id,
        planning_slot_id=event.id,
        title=event.title,
        description=event.description,
        actual_start_at=event.start_at,
        actual_end_at=event.end_at,
        source=event.source,
        visibility=event.visibility,
        deviation_flag=False,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _planning_slot_status(status: EventStatus) -> PlanningSlotStatus:
    if status == EventStatus.CANCELLED:
        return PlanningSlotStatus.CANCELLED
    return PlanningSlotStatus.ACTIVE
