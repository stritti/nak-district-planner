from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.congregation import CongregationORM
from app.domain.models.congregation import Congregation
from app.domain.ports.repositories import CongregationRepository


def _orm_to_domain(row: CongregationORM) -> Congregation:
    return Congregation(
        id=row.id,
        name=row.name,
        district_id=row.district_id,
        service_times=list(row.service_times) if row.service_times else [],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlCongregationRepository(CongregationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, congregation_id: uuid.UUID) -> Congregation | None:
        row = await self._session.get(CongregationORM, congregation_id)
        return _orm_to_domain(row) if row else None

    async def list_by_district(self, district_id: uuid.UUID) -> list[Congregation]:
        result = await self._session.execute(
            select(CongregationORM)
            .where(CongregationORM.district_id == district_id)
            .order_by(CongregationORM.name)
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def save(self, congregation: Congregation) -> None:
        existing = await self._session.get(CongregationORM, congregation.id)
        if existing is None:
            row = CongregationORM()
            self._session.add(row)
        else:
            row = existing
        row.id = congregation.id
        row.name = congregation.name
        row.district_id = congregation.district_id
        row.service_times = congregation.service_times
        row.created_at = congregation.created_at
        row.updated_at = congregation.updated_at
        await self._session.flush()
