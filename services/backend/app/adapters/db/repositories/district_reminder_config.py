# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Async repository for monthly reminder configuration."""

from __future__ import annotations

import uuid
from typing import ClassVar

from sqlalchemy import select

from app.adapters.db.orm_models.district_reminder_config import DistrictReminderConfigORM
from app.adapters.db.repository_base import SqlRepository
from app.domain.models.district_reminder_config import DistrictReminderConfig
from app.domain.models.role import Role


def _to_domain(row: DistrictReminderConfigORM) -> DistrictReminderConfig:
    return DistrictReminderConfig(
        id=row.id,
        district_id=row.district_id,
        day_of_month=row.day_of_month,
        time_of_day=row.time_of_day,
        subject_template=row.subject_template,
        body_template=row.body_template,
        recipient_role=Role(row.recipient_role),
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlDistrictReminderConfigRepository(SqlRepository[DistrictReminderConfigORM, DistrictReminderConfig]):
    orm_type = DistrictReminderConfigORM
    _fields: ClassVar[dict[str, str]] = {
        "id": "id",
        "district_id": "district_id",
        "day_of_month": "day_of_month",
        "time_of_day": "time_of_day",
        "subject_template": "subject_template",
        "body_template": "body_template",
        "recipient_role": "recipient_role",
        "is_active": "is_active",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }


    async def get(self, district_id: uuid.UUID, config_id: uuid.UUID) -> DistrictReminderConfig | None:
        result = await self._session.execute(
            select(DistrictReminderConfigORM).where(
                DistrictReminderConfigORM.id == config_id,
                DistrictReminderConfigORM.district_id == district_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def get_for_update(
        self, district_id: uuid.UUID, config_id: uuid.UUID
    ) -> DistrictReminderConfig | None:
        """Read the latest state while holding a row lock through the transaction."""
        result = await self._session.execute(
            select(DistrictReminderConfigORM)
            .where(
                DistrictReminderConfigORM.id == config_id,
                DistrictReminderConfigORM.district_id == district_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_by_district(self, district_id: uuid.UUID) -> list[DistrictReminderConfig]:
        result = await self._session.execute(
            select(DistrictReminderConfigORM)
            .where(DistrictReminderConfigORM.district_id == district_id)
            .order_by(DistrictReminderConfigORM.created_at, DistrictReminderConfigORM.id)
        )
        return [_to_domain(row) for row in result.scalars().all()]

    async def list_active(self) -> list[DistrictReminderConfig]:
        result = await self._session.execute(
            select(DistrictReminderConfigORM)
            .where(DistrictReminderConfigORM.is_active.is_(True))
            .order_by(DistrictReminderConfigORM.district_id, DistrictReminderConfigORM.id)
        )
        return [_to_domain(row) for row in result.scalars().all()]

