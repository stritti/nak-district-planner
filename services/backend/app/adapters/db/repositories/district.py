from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.district import DistrictORM
from app.domain.models.district import District
from app.domain.ports.repositories import DistrictRepository


def _orm_to_domain(row: DistrictORM) -> District:
    return District(
        id=row.id,
        name=row.name,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlDistrictRepository(DistrictRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, district_id: uuid.UUID) -> District | None:
        row = await self._session.get(DistrictORM, district_id)
        return _orm_to_domain(row) if row else None

    async def list_all(self) -> list[District]:
        result = await self._session.execute(select(DistrictORM).order_by(DistrictORM.name))
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def save(self, district: District) -> None:
        existing = await self._session.get(DistrictORM, district.id)
        if existing is None:
            row = DistrictORM()
            self._session.add(row)
        else:
            row = existing
        row.id = district.id
        row.name = district.name
        row.created_at = district.created_at
        row.updated_at = district.updated_at
        await self._session.flush()
