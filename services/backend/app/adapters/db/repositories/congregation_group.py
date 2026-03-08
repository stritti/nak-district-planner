from __future__ import annotations

import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.congregation_group import CongregationGroupORM
from app.domain.models.congregation_group import CongregationGroup
from app.domain.ports.repositories import CongregationGroupRepository


def _orm_to_domain(row: CongregationGroupORM) -> CongregationGroup:
    return CongregationGroup(
        id=row.id,
        name=row.name,
        district_id=row.district_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlCongregationGroupRepository(CongregationGroupRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, group_id: uuid.UUID) -> CongregationGroup | None:
        row = await self._session.get(CongregationGroupORM, group_id)
        return _orm_to_domain(row) if row else None

    async def list_by_district(self, district_id: uuid.UUID) -> list[CongregationGroup]:
        result = await self._session.execute(
            select(CongregationGroupORM)
            .where(CongregationGroupORM.district_id == district_id)
            .order_by(CongregationGroupORM.name)
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def save(self, group: CongregationGroup) -> None:
        existing = await self._session.get(CongregationGroupORM, group.id)
        if existing is None:
            row = CongregationGroupORM()
            self._session.add(row)
        else:
            row = existing
        row.id = group.id
        row.name = group.name
        row.district_id = group.district_id
        row.created_at = group.created_at
        row.updated_at = group.updated_at
        await self._session.flush()

    async def delete(self, group_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(CongregationGroupORM).where(CongregationGroupORM.id == group_id)
        )
        await self._session.flush()
