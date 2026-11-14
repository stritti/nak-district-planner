# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/db/repositories/congregation.py: Module."""

from __future__ import annotations

import uuid
from typing import ClassVar

from sqlalchemy import select

from app.adapters.db.orm_models.congregation import CongregationORM
from app.adapters.db.repository_base import SqlRepository
from app.domain.models.congregation import Congregation
from app.domain.models.invitation import InvitationTargetType
from app.domain.ports.repositories import CongregationRepository


def _orm_to_domain(row: CongregationORM) -> Congregation:
    return Congregation(
        id=row.id,
        name=row.name,
        district_id=row.district_id,
        service_times=list(row.service_times) if row.service_times else [],
        created_at=row.created_at,
        updated_at=row.updated_at,
        group_id=row.group_id,
        invitation_target_type=InvitationTargetType(row.invitation_target_type)
        if row.invitation_target_type
        else None,
        invitation_target_congregation_id=row.invitation_target_congregation_id,
        invitation_external_note=row.invitation_external_note,
    )


class SqlCongregationRepository(SqlRepository[CongregationORM, Congregation], CongregationRepository):
    """SQLAlchemy repository for Congregation."""

    orm_type = CongregationORM
    _fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "name": "name",
        "district_id": "district_id",
        "group_id": "group_id",
        "service_times": "service_times",
        "invitation_target_type": "invitation_target_type",
        "invitation_target_congregation_id": "invitation_target_congregation_id",
        "invitation_external_note": "invitation_external_note",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }



    async def get(self, congregation_id: uuid.UUID) -> Congregation | None:
        row = await self._session.get(CongregationORM, congregation_id)
        return _orm_to_domain(row) if row else None

    async def get_for_update(self, congregation_id: uuid.UUID) -> Congregation | None:
        """Read the latest state while holding a row lock through the transaction."""
        row = await self._session.get(
            CongregationORM, congregation_id, with_for_update=True, populate_existing=True
        )
        return _orm_to_domain(row) if row else None

    async def list_by_district(
        self, district_id: uuid.UUID, group_id: uuid.UUID | None = None
    ) -> list[Congregation]:
        stmt = select(CongregationORM).where(CongregationORM.district_id == district_id)
        if group_id is not None:
            stmt = stmt.where(CongregationORM.group_id == group_id)
        stmt = stmt.order_by(CongregationORM.name)
        result = await self._session.execute(stmt)
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_by_ids(self, congregation_ids: list[uuid.UUID]) -> list[Congregation]:
        if not congregation_ids:
            return []
        stmt = select(CongregationORM).where(CongregationORM.id.in_(congregation_ids))
        result = await self._session.execute(stmt)
        return [_orm_to_domain(r) for r in result.scalars().all()]

