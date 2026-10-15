# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Build conflict contexts for service-assignment use cases."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.leader_unavailability import (
    SqlLeaderUnavailabilityRepository,
)
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.config import settings
from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import PlanningSlot
from app.domain.planning.conflict_result import (
    ConflictContext,
    ExistingAssignment,
    ScheduledService,
)
from app.domain.planning.conflict_service import ConflictService


@dataclass(frozen=True)
class ProposedService:
    """Schedule of a planning slot as it would be after a pending change."""

    congregation_id: uuid.UUID | None
    planning_date: date
    planning_time: time | None
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None

    @classmethod
    def of(cls, slot: PlanningSlot, instance: EventInstance | None) -> ProposedService:
        return cls(
            congregation_id=slot.congregation_id,
            planning_date=slot.planning_date,
            planning_time=slot.planning_time,
            actual_start_at=instance.actual_start_at if instance else None,
            actual_end_at=instance.actual_end_at if instance else None,
        )


async def check_service_assignment_conflicts(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    leader_id: uuid.UUID,
    exclude_assignment_id: uuid.UUID | None = None,
    proposed: ProposedService | None = None,
) -> list:
    """Evaluate conflicts for assigning a leader to a planning slot.

    Fail-closed: slots without EventInstance are compared by their planned
    time and the configured default duration instead of being skipped.
    """
    if not settings.conflict_check_enabled:
        return []

    if proposed is None:
        slot = await SqlPlanningSlotRepository(session).get(event_id)
        if slot is None:
            return []
        instance = await SqlEventInstanceRepository(session).get_by_planning_slot(event_id)
        proposed = ProposedService.of(slot, instance)
    leader = await SqlLeaderRepository(session).get(leader_id)

    default_duration = timedelta(minutes=settings.sync_expected_duration_minutes)
    start, end = ScheduledService(
        congregation_id=proposed.congregation_id,
        planning_date=proposed.planning_date,
        planning_time=proposed.planning_time,
        actual_start_at=proposed.actual_start_at,
        actual_end_at=proposed.actual_end_at,
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
        congregation_id=proposed.congregation_id,
        existing_assignments=existing,
        leader_rank=leader.rank.value if leader and leader.rank else None,
        min_travel_minutes=settings.min_travel_minutes,
        unavailability_periods=tuple((item.start_at, item.end_at) for item in unavailability),
    )
    return ConflictService().check(context)
