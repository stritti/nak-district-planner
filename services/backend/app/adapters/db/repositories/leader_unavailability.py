"""SQLAlchemy repository for leader unavailability periods."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.leader_unavailability import LeaderUnavailabilityORM
from app.domain.models.leader_unavailability import LeaderUnavailability, UnavailabilityReason
from app.domain.ports.repositories import LeaderUnavailabilityRepository


def _orm_to_domain(row: LeaderUnavailabilityORM) -> LeaderUnavailability:
    return LeaderUnavailability(
        id=row.id,
        leader_id=row.leader_id,
        start_at=row.start_at,
        end_at=row.end_at,
        reason=UnavailabilityReason(row.reason),
        note=row.note,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlLeaderUnavailabilityRepository(LeaderUnavailabilityRepository):
    """SQLAlchemy repository for leader unavailability periods."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, unavailability_id: uuid.UUID) -> LeaderUnavailability | None:
        row = await self._session.get(LeaderUnavailabilityORM, unavailability_id)
        return _orm_to_domain(row) if row else None

    async def list_by_leader(self, leader_id: uuid.UUID) -> list[LeaderUnavailability]:
        result = await self._session.execute(
            select(LeaderUnavailabilityORM)
            .where(LeaderUnavailabilityORM.leader_id == leader_id)
            .order_by(LeaderUnavailabilityORM.start_at)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def list_overlapping(
        self,
        *,
        leader_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> list[LeaderUnavailability]:
        result = await self._session.execute(
            select(LeaderUnavailabilityORM)
            .where(
                LeaderUnavailabilityORM.leader_id == leader_id,
                LeaderUnavailabilityORM.start_at < end_at,
                LeaderUnavailabilityORM.end_at > start_at,
            )
            .order_by(LeaderUnavailabilityORM.start_at)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def save(self, unavailability: LeaderUnavailability) -> None:
        row = await self._session.get(LeaderUnavailabilityORM, unavailability.id)
        if row is None:
            row = LeaderUnavailabilityORM()
            self._session.add(row)
        row.id = unavailability.id
        row.leader_id = unavailability.leader_id
        row.start_at = unavailability.start_at
        row.end_at = unavailability.end_at
        row.reason = unavailability.reason.value
        row.note = unavailability.note
        row.created_at = unavailability.created_at
        row.updated_at = unavailability.updated_at
        await self._session.flush()

    async def delete(self, unavailability_id: uuid.UUID) -> None:
        row = await self._session.get(LeaderUnavailabilityORM, unavailability_id)
        if row is not None:
            await self._session.delete(row)
