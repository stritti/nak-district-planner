"""Build conflict contexts for service-assignment use cases."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.leader_unavailability import (
    SqlLeaderUnavailabilityRepository,
)
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.config import settings
from app.domain.planning.conflict_result import (
    ConflictContext,
    ExistingAssignment,
    ScheduledService,
)
from app.domain.planning.conflict_service import ConflictService


async def check_service_assignment_conflicts(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    leader_id: uuid.UUID,
    exclude_assignment_id: uuid.UUID | None = None,
) -> list:
    """Evaluate conflicts for assigning a leader to a planning slot.

    Fail-closed: slots without EventInstance are compared by their planned
    time and the configured default duration instead of being skipped.
    """
    if not settings.conflict_check_enabled:
        return []

    slot = await SqlPlanningSlotRepository(session).get(event_id)
    if slot is None:
        return []
    instance = await SqlEventInstanceRepository(session).get_by_planning_slot(event_id)
    leader = await SqlLeaderRepository(session).get(leader_id)

    default_duration = timedelta(minutes=settings.sync_expected_duration_minutes)
    start, end = ScheduledService(
        congregation_id=slot.congregation_id,
        planning_date=slot.planning_date,
        planning_time=slot.planning_time,
        actual_start_at=instance.actual_start_at if instance else None,
        actual_end_at=instance.actual_end_at if instance else None,
    ).window(default_duration)

    # A service without EventInstance lasts default_duration, so one starting up to
    # that long before the target can still overlap it; add the travel-time margin.
    margin = default_duration + timedelta(minutes=settings.min_travel_minutes)
    schedule = await SqlServiceAssignmentRepository(session).list_leader_schedule(
        leader_id,
        window_start=start - margin,
        window_end=end + margin,
        exclude_assignment_id=exclude_assignment_id,
    )
    existing = tuple(
        ExistingAssignment(leader_id, *service.window(default_duration), service.congregation_id)
        for service in schedule
    )
    unavailability = await SqlLeaderUnavailabilityRepository(session).list_overlapping(
        leader_id=leader_id, start_at=start, end_at=end
    )
    context = ConflictContext(
        leader_id=leader_id,
        start_time=start,
        end_time=end,
        congregation_id=slot.congregation_id,
        existing_assignments=existing,
        leader_rank=leader.rank.value if leader and leader.rank else None,
        min_travel_minutes=settings.min_travel_minutes,
        unavailability_periods=tuple((item.start_at, item.end_at) for item in unavailability),
    )
    return ConflictService().check(context)
