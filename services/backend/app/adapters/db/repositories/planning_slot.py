from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.repositories import PlanningSlotRepository


def _orm_to_domain(row: PlanningSlotORM) -> PlanningSlot:
    return PlanningSlot(
        id=row.id,
        series_id=row.series_id,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        category=row.category,
        planning_date=row.planning_date,
        planning_time=row.planning_time,
        status=PlanningSlotStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlPlanningSlotRepository(PlanningSlotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, slot_id: uuid.UUID) -> PlanningSlot | None:
        row = await self._session.get(PlanningSlotORM, slot_id)
        return _orm_to_domain(row) if row else None

    async def list_for_date_range(
        self,
        *,
        district_id: uuid.UUID,
        from_date: date,
        to_date: date,
    ) -> list[PlanningSlot]:
        result = await self._session.execute(
            select(PlanningSlotORM)
            .where(
                PlanningSlotORM.district_id == district_id,
                PlanningSlotORM.planning_date >= from_date,
                PlanningSlotORM.planning_date <= to_date,
            )
            .order_by(PlanningSlotORM.planning_date, PlanningSlotORM.planning_time)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def save(self, slot: PlanningSlot) -> None:
        existing = await self._session.get(PlanningSlotORM, slot.id)
        row = existing or PlanningSlotORM()
        row.id = slot.id
        row.series_id = slot.series_id
        row.district_id = slot.district_id
        row.congregation_id = slot.congregation_id
        row.category = slot.category
        row.planning_date = slot.planning_date
        row.planning_time = slot.planning_time
        row.status = slot.status
        row.created_at = slot.created_at
        row.updated_at = slot.updated_at
        if existing is None:
            self._session.add(row)
        await self._session.flush()
