"""app/adapters/db/repositories/service_assignment.py: Module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.event_instance import EventInstanceORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.domain.models.planning_slot import PlanningSlotStatus
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment
from app.domain.planning.conflict_result import ScheduledService
from app.domain.ports.repositories import ServiceAssignmentRepository


def _orm_to_domain(row: ServiceAssignmentORM) -> ServiceAssignment:
    return ServiceAssignment(
        id=row.id,
        event_id=row.event_id,
        planning_slot_id=row.planning_slot_id,
        leader_id=row.leader_id,
        leader_name=row.leader_name,
        status=AssignmentStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlServiceAssignmentRepository(ServiceAssignmentRepository):
    """SQLAlchemy repository for ServiceAssignment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, assignment_id: uuid.UUID) -> ServiceAssignment | None:
        row = await self._session.get(ServiceAssignmentORM, assignment_id)
        return _orm_to_domain(row) if row else None

    async def list_by_planning_slot(self, slot_or_event_id: uuid.UUID) -> list[ServiceAssignment]:
        # Check the canonical planning-slot key first, then fall back to legacy event linkage.
        result = await self._session.execute(
            select(ServiceAssignmentORM).where(
                or_(
                    ServiceAssignmentORM.planning_slot_id == slot_or_event_id,
                    ServiceAssignmentORM.event_id == slot_or_event_id,
                )
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_by_planning_slots(
        self, slot_or_event_ids: list[uuid.UUID]
    ) -> list[ServiceAssignment]:
        if not slot_or_event_ids:
            return []
        # Check canonical planning-slot linkage first; `event_id` remains a compatibility fallback.
        result = await self._session.execute(
            select(ServiceAssignmentORM).where(
                or_(
                    ServiceAssignmentORM.planning_slot_id.in_(slot_or_event_ids),
                    ServiceAssignmentORM.event_id.in_(slot_or_event_ids),
                )
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_by_leader(self, leader_id: uuid.UUID) -> list[ServiceAssignment]:
        result = await self._session.execute(
            select(ServiceAssignmentORM).where(ServiceAssignmentORM.leader_id == leader_id)
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_leader_schedule(
        self,
        leader_id: uuid.UUID,
        *,
        window_start: datetime,
        window_end: datetime,
        exclude_assignment_id: uuid.UUID | None = None,
    ) -> list[ScheduledService]:
        """Active services of a leader near a time window, in one query.

        A service matches when its EventInstance overlaps the window or, when it
        has no instance yet, when its planning date lies inside the window's dates.
        """
        slot_id = func.coalesce(ServiceAssignmentORM.planning_slot_id, ServiceAssignmentORM.event_id)
        query = (
            select(
                PlanningSlotORM.congregation_id,
                PlanningSlotORM.planning_date,
                PlanningSlotORM.planning_time,
                EventInstanceORM.actual_start_at,
                EventInstanceORM.actual_end_at,
            )
            .select_from(ServiceAssignmentORM)
            .join(PlanningSlotORM, PlanningSlotORM.id == slot_id)
            .outerjoin(EventInstanceORM, EventInstanceORM.planning_slot_id == PlanningSlotORM.id)
            .where(
                ServiceAssignmentORM.leader_id == leader_id,
                PlanningSlotORM.status == PlanningSlotStatus.ACTIVE,
                or_(
                    and_(
                        EventInstanceORM.id.is_not(None),
                        EventInstanceORM.actual_start_at < window_end,
                        EventInstanceORM.actual_end_at > window_start,
                    ),
                    and_(
                        EventInstanceORM.id.is_(None),
                        PlanningSlotORM.planning_date.between(
                            window_start.astimezone(UTC).date(), window_end.astimezone(UTC).date()
                        ),
                    ),
                ),
            )
        )
        if exclude_assignment_id is not None:
            query = query.where(ServiceAssignmentORM.id != exclude_assignment_id)
        result = await self._session.execute(query)
        return [ScheduledService(*row) for row in result.all()]

    async def save(self, assignment: ServiceAssignment) -> None:
        existing = await self._session.get(ServiceAssignmentORM, assignment.id)
        if existing is None:
            row = ServiceAssignmentORM()
            self._session.add(row)
        else:
            row = existing
        row.id = assignment.id
        row.event_id = assignment.event_id
        row.planning_slot_id = assignment.planning_slot_id
        row.leader_id = assignment.leader_id
        row.leader_name = assignment.leader_name
        row.status = assignment.status
        row.created_at = assignment.created_at
        row.updated_at = assignment.updated_at
        await self._session.flush()

    async def delete(self, assignment_id: uuid.UUID) -> None:
        row = await self._session.get(ServiceAssignmentORM, assignment_id)
        if row is None:
            return
        await self._session.delete(row)
        await self._session.flush()
