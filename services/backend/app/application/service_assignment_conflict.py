"""Build conflict contexts for service-assignment use cases."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.leader_unavailability import (
    SqlLeaderUnavailabilityRepository,
)
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.config import settings
from app.domain.planning.conflict_result import ConflictContext, ExistingAssignment
from app.domain.planning.conflict_service import ConflictService


async def check_service_assignment_conflicts(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    leader_id: uuid.UUID,
    exclude_assignment_id: uuid.UUID | None = None,
) -> list:
    """Evaluate conflicts for assigning a leader to a planning slot."""
    if not settings.conflict_check_enabled:
        return []

    slot_repo = SqlPlanningSlotRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    assignment_repo = SqlServiceAssignmentRepository(session)
    leader_repo = SqlLeaderRepository(session)
    absence_repo = SqlLeaderUnavailabilityRepository(session)

    slot = await slot_repo.get(event_id)
    instance = await instance_repo.get_by_planning_slot(event_id)
    leader = await leader_repo.get(leader_id)
    if slot is None or instance is None or leader is None:
        return []

    assignments = await assignment_repo.list_by_leader(leader_id)
    existing: list[ExistingAssignment] = []
    for assignment in assignments:
        if assignment.id == exclude_assignment_id:
            continue
        assignment_slot_id = assignment.planning_slot_id or assignment.event_id
        assignment_slot = await slot_repo.get(assignment_slot_id)
        assignment_instance = await instance_repo.get_by_planning_slot(assignment_slot_id)
        if assignment_slot is None or assignment_instance is None:
            continue
        existing.append(
            ExistingAssignment(
                leader_id=leader_id,
                start_time=assignment_instance.actual_start_at,
                end_time=assignment_instance.actual_end_at,
                congregation_id=assignment_slot.congregation_id,
            )
        )

    unavailability = await absence_repo.list_overlapping(
        leader_id=leader_id,
        start_at=instance.actual_start_at,
        end_at=instance.actual_end_at,
    )
    context = ConflictContext(
        leader_id=leader_id,
        start_time=instance.actual_start_at,
        end_time=instance.actual_end_at,
        congregation_id=slot.congregation_id,
        existing_assignments=tuple(existing),
        leader_rank=leader.rank.value if leader.rank else None,
        min_travel_minutes=settings.min_travel_minutes,
        unavailability_periods=tuple((item.start_at, item.end_at) for item in unavailability),
    )
    return ConflictService().check(context)
