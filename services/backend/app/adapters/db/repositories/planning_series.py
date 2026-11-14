# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import uuid
from datetime import date
from typing import ClassVar

from sqlalchemy import select

from app.adapters.db.orm_models.planning_series import PlanningSeriesORM
from app.adapters.db.repository_base import SqlRepository
from app.domain.models.planning_series import PlanningSeries
from app.domain.ports.repositories import PlanningSeriesRepository


def _orm_to_domain(row: PlanningSeriesORM) -> PlanningSeries:
    return PlanningSeries(
        id=row.id,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        category=row.category,
        default_planning_time=row.default_planning_time,
        recurrence_pattern=dict(row.recurrence_pattern or {}),
        active_from=row.active_from,
        active_until=row.active_until,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlPlanningSeriesRepository(SqlRepository[PlanningSeriesORM, PlanningSeries], PlanningSeriesRepository):
    orm_type = PlanningSeriesORM
    _fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "district_id": "district_id",
        "congregation_id": "congregation_id",
        "category": "category",
        "default_planning_time": "default_planning_time",
        "recurrence_pattern": "recurrence_pattern",
        "active_from": "active_from",
        "active_until": "active_until",
        "is_active": "is_active",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }


    async def get(self, series_id: uuid.UUID) -> PlanningSeries | None:
        row = await self._session.get(PlanningSeriesORM, series_id)
        return _orm_to_domain(row) if row else None

    async def list_all(self) -> list[PlanningSeries]:
        """List all PlanningSeries across all districts."""
        result = await self._session.execute(
            select(PlanningSeriesORM).order_by(
                PlanningSeriesORM.district_id, PlanningSeriesORM.created_at
            )
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def list_by_district(self, district_id: uuid.UUID) -> list[PlanningSeries]:
        """List all PlanningSeries for a district."""
        result = await self._session.execute(
            select(PlanningSeriesORM)
            .where(PlanningSeriesORM.district_id == district_id)
            .order_by(PlanningSeriesORM.created_at)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def list_all_active(self) -> list[PlanningSeries]:
        """List all active PlanningSeries across all districts."""
        result = await self._session.execute(
            select(PlanningSeriesORM)
            .where(PlanningSeriesORM.is_active)
            .order_by(PlanningSeriesORM.district_id, PlanningSeriesORM.created_at)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

    async def list_active(self) -> list[PlanningSeries]:
        """List all active PlanningSeries with valid date range."""
        today = date.today()
        result = await self._session.execute(
            select(PlanningSeriesORM)
            .where(PlanningSeriesORM.is_active.is_(True))
            .where(
                PlanningSeriesORM.active_from.is_(None) | (PlanningSeriesORM.active_from <= today)
            )
            .where(
                PlanningSeriesORM.active_until.is_(None) | (PlanningSeriesORM.active_until >= today)
            )
            .order_by(PlanningSeriesORM.district_id, PlanningSeriesORM.created_at)
        )
        return [_orm_to_domain(row) for row in result.scalars().all()]

