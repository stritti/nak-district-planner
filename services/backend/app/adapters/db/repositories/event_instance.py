from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.event_instance import EventInstanceORM
from app.domain.models.event import EventSource, EventVisibility
from app.domain.models.event_instance import EventInstance
from app.domain.ports.repositories import EventInstanceRepository


def _orm_to_domain(row: EventInstanceORM) -> EventInstance:
    return EventInstance(
        id=row.id,
        planning_slot_id=row.planning_slot_id,
        title=row.title,
        description=row.description,
        actual_start_at=row.actual_start_at,
        actual_end_at=row.actual_end_at,
        source=EventSource(row.source),
        visibility=EventVisibility(row.visibility),
        deviation_flag=row.deviation_flag,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlEventInstanceRepository(EventInstanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, instance_id: uuid.UUID) -> EventInstance | None:
        row = await self._session.get(EventInstanceORM, instance_id)
        return _orm_to_domain(row) if row else None

    async def list_by_planning_slots(self, slot_ids: list[uuid.UUID]) -> list[EventInstance]:
        if not slot_ids:
            return []
        result = await self._session.execute(
            select(EventInstanceORM).where(EventInstanceORM.planning_slot_id.in_(slot_ids))
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def save(self, instance: EventInstance) -> None:
        existing = await self._session.get(EventInstanceORM, instance.id)
        row = existing or EventInstanceORM()
        row.id = instance.id
        row.planning_slot_id = instance.planning_slot_id
        row.title = instance.title
        row.description = instance.description
        row.actual_start_at = instance.actual_start_at
        row.actual_end_at = instance.actual_end_at
        row.source = instance.source
        row.visibility = instance.visibility
        row.deviation_flag = instance.deviation_flag
        row.created_at = instance.created_at
        row.updated_at = instance.updated_at
        if existing is None:
            self._session.add(row)
        await self._session.flush()
