from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment
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
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, assignment_id: uuid.UUID) -> ServiceAssignment | None:
        row = await self._session.get(ServiceAssignmentORM, assignment_id)
        return _orm_to_domain(row) if row else None

    async def list_by_event(self, planning_slot_id: uuid.UUID) -> list[ServiceAssignment]:
        result = await self._session.execute(
            select(ServiceAssignmentORM).where(
                ServiceAssignmentORM.planning_slot_id == planning_slot_id
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_by_events(self, planning_slot_ids: list[uuid.UUID]) -> list[ServiceAssignment]:
        if not planning_slot_ids:
            return []
        result = await self._session.execute(
            select(ServiceAssignmentORM).where(
                ServiceAssignmentORM.planning_slot_id.in_(planning_slot_ids)
            )
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

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
