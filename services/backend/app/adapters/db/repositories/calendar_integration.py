from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.calendar_integration import CalendarIntegrationORM
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.ports.repositories import CalendarIntegrationRepository


def _orm_to_domain(row: CalendarIntegrationORM) -> CalendarIntegration:
    return CalendarIntegration(
        id=row.id,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        name=row.name,
        type=CalendarType(row.type),
        credentials_enc=row.credentials_enc,
        sync_interval=row.sync_interval,
        capabilities=[CalendarCapability(c) for c in (row.capabilities or [])],
        is_active=row.is_active,
        last_synced_at=row.last_synced_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        default_category=row.default_category,
    )


def _domain_to_orm(
    integration: CalendarIntegration, existing: CalendarIntegrationORM | None = None
) -> CalendarIntegrationORM:
    row = existing or CalendarIntegrationORM()
    row.id = integration.id
    row.district_id = integration.district_id
    row.congregation_id = integration.congregation_id
    row.name = integration.name
    row.type = integration.type
    row.credentials_enc = integration.credentials_enc
    row.sync_interval = integration.sync_interval
    row.capabilities = [c.value for c in integration.capabilities]
    row.is_active = integration.is_active
    row.last_synced_at = integration.last_synced_at
    row.created_at = integration.created_at
    row.updated_at = integration.updated_at
    row.default_category = integration.default_category
    return row


class SqlCalendarIntegrationRepository(CalendarIntegrationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, integration_id: uuid.UUID) -> CalendarIntegration | None:
        row = await self._session.get(CalendarIntegrationORM, integration_id)
        return _orm_to_domain(row) if row else None

    async def list_by_district(self, district_id: uuid.UUID) -> list[CalendarIntegration]:
        result = await self._session.execute(
            select(CalendarIntegrationORM)
            .where(CalendarIntegrationORM.district_id == district_id)
            .order_by(CalendarIntegrationORM.name)
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def list_active(self) -> list[CalendarIntegration]:
        result = await self._session.execute(
            select(CalendarIntegrationORM)
            .where(CalendarIntegrationORM.is_active.is_(True))
            .order_by(CalendarIntegrationORM.id)
        )
        return [_orm_to_domain(r) for r in result.scalars().all()]

    async def save(self, integration: CalendarIntegration) -> None:
        existing = await self._session.get(CalendarIntegrationORM, integration.id)
        row = _domain_to_orm(integration, existing)
        if existing is None:
            self._session.add(row)
        await self._session.flush()

    async def delete(self, integration_id: uuid.UUID) -> None:
        row = await self._session.get(CalendarIntegrationORM, integration_id)
        if row is not None:
            await self._session.delete(row)
            await self._session.flush()
