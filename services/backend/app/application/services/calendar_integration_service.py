"""Application service for calendar integrations."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.schemas.calendar_integration import (
    CalendarIntegrationCreate,
    CalendarIntegrationUpdate,
)
from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
from app.application.crypto import encrypt_credentials
from app.domain.models.calendar_integration import CalendarIntegration


class CalendarIntegrationService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = SqlCalendarIntegrationRepository(db)

    async def create_integration(self, body: CalendarIntegrationCreate) -> CalendarIntegration:
        integration = CalendarIntegration.create(
            district_id=body.district_id,
            congregation_id=body.congregation_id,
            name=body.name,
            type=body.type,
            credentials_enc=encrypt_credentials(body.credentials),
            sync_interval=body.sync_interval,
            capabilities=body.capabilities,
            default_category=body.default_category,
        )
        await self._repo.save(integration)
        return integration

    async def update_integration(
        self,
        integration: CalendarIntegration,
        body: CalendarIntegrationUpdate,
    ) -> CalendarIntegration:
        fields = body.model_fields_set
        if "name" in fields and body.name is not None:
            integration.name = body.name
        if "credentials" in fields and body.credentials is not None:
            integration.credentials_enc = encrypt_credentials(body.credentials)
        if "sync_interval" in fields and body.sync_interval is not None:
            integration.sync_interval = body.sync_interval
        if "capabilities" in fields and body.capabilities is not None:
            integration.capabilities = body.capabilities
        if "default_category" in fields:
            integration.default_category = body.default_category

        await self._repo.save(integration)
        return integration
