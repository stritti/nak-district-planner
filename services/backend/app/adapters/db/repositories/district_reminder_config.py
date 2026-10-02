"""Async repository for monthly reminder configuration."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.district_reminder_config import DistrictReminderConfigORM
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


class SqlDistrictReminderConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, district_id: uuid.UUID, config_id: uuid.UUID) -> DistrictReminderConfig | None:
        result = await self._session.execute(
            select(DistrictReminderConfigORM).where(
                DistrictReminderConfigORM.id == config_id,
                DistrictReminderConfigORM.district_id == district_id,
            )
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

    async def save(self, config: DistrictReminderConfig) -> None:
        row = await self._session.get(DistrictReminderConfigORM, config.id)
        if row is None:
            row = DistrictReminderConfigORM(id=config.id)
            self._session.add(row)
        row.district_id = config.district_id
        row.day_of_month = config.day_of_month
        row.time_of_day = config.time_of_day
        row.subject_template = config.subject_template
        row.body_template = config.body_template
        row.recipient_role = config.recipient_role.value
        row.is_active = config.is_active
        row.created_at = config.created_at
        row.updated_at = config.updated_at
        await self._session.flush()
