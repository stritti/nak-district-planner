from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.leader import LeaderORM
from app.domain.models.leader import Leader, LeaderRank, SpecialRole
from app.domain.ports.repositories import LeaderRepository


def _orm_to_domain(row: LeaderORM) -> Leader:
    return Leader(
        id=row.id,
        name=row.name,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        rank=LeaderRank(row.rank) if row.rank else None,
        special_role=SpecialRole(row.special_role) if row.special_role else None,
        email=row.email,
        phone=row.phone,
        notes=row.notes,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlLeaderRepository(LeaderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, leader_id: uuid.UUID) -> Leader | None:
        row = await self._session.get(LeaderORM, leader_id)
        return _orm_to_domain(row) if row else None

    async def list_by_district(
        self,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID | None = None,
        active_only: bool = False,
    ) -> list[Leader]:
        stmt = select(LeaderORM).where(LeaderORM.district_id == district_id)
        if congregation_id is not None:
            stmt = stmt.where(LeaderORM.congregation_id == congregation_id)
        if active_only:
            stmt = stmt.where(LeaderORM.is_active.is_(True))
        stmt = stmt.order_by(LeaderORM.name)
        result = await self._session.execute(stmt)
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def save(self, leader: Leader) -> None:
        existing = await self._session.get(LeaderORM, leader.id)
        if existing is None:
            row = LeaderORM()
            self._session.add(row)
        else:
            row = existing
        row.id = leader.id
        row.name = leader.name
        row.district_id = leader.district_id
        row.congregation_id = leader.congregation_id
        row.rank = leader.rank.value if leader.rank else None
        row.special_role = leader.special_role.value if leader.special_role else None
        row.email = leader.email
        row.phone = leader.phone
        row.notes = leader.notes
        row.is_active = leader.is_active
        row.created_at = leader.created_at
        row.updated_at = leader.updated_at
        await self._session.flush()

    async def delete(self, leader_id: uuid.UUID) -> None:
        row = await self._session.get(LeaderORM, leader_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()
