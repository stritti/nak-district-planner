# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLAlchemy repository for leader unavailability periods."""

from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import ClassVar

from sqlalchemy import select

from app.adapters.db.orm_models.leader_unavailability import LeaderUnavailabilityORM
from app.adapters.db.repository_base import SqlRepository
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


class SqlLeaderUnavailabilityRepository(SqlRepository[LeaderUnavailabilityORM, LeaderUnavailability], LeaderUnavailabilityRepository):
    """SQLAlchemy repository for leader unavailability periods."""

    orm_type = LeaderUnavailabilityORM
    _fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "leader_id": "leader_id",
        "start_at": "start_at",
        "end_at": "end_at",
        "reason": "reason",
        "note": "note",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }



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

    async def list_overlapping_for_leaders(
        self,
        *,
        leader_ids: Collection[uuid.UUID],
        start_at: datetime,
        end_at: datetime,
    ) -> list[LeaderUnavailability]:
        if not leader_ids:
            return []
        result = await self._session.execute(
            select(LeaderUnavailabilityORM)
            .where(
                LeaderUnavailabilityORM.leader_id.in_(list(leader_ids)),
                LeaderUnavailabilityORM.start_at < end_at,
                LeaderUnavailabilityORM.end_at > start_at,
            )
            .order_by(LeaderUnavailabilityORM.start_at)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]


    async def delete(self, unavailability_id: uuid.UUID) -> None:
        row = await self._session.get(LeaderUnavailabilityORM, unavailability_id)
        if row is not None:
            await self._session.delete(row)
