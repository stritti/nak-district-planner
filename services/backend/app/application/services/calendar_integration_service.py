# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Application service for calendar integrations."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.services.calendar_integration_commands import (
    CalendarIntegrationCreateCommand,
    CalendarIntegrationUpdateCommand,
)
from app.application.crypto import encrypt_credentials
from app.domain.models.calendar_integration import CalendarIntegration
from app.domain.ports.repositories import CalendarIntegrationRepository


class CalendarIntegrationService:
    def __init__(self, repository: CalendarIntegrationRepository) -> None:
        self._repo = repository

    async def create_integration(self, body: CalendarIntegrationCreateCommand) -> CalendarIntegration:
        integration = CalendarIntegration.create(
            district_id=body.district_id,
            congregation_id=body.congregation_id,
            name=body.name,
            type=body.type,
            credentials_enc=encrypt_credentials(body.credentials),
            sync_interval=body.sync_interval,
            capabilities=body.capabilities,
            default_category=body.default_category,
            delete_behavior=body.delete_behavior,
        )
        await self._repo.save(integration)
        return integration

    async def update_integration(
        self,
        integration: CalendarIntegration,
        body: CalendarIntegrationUpdateCommand,
    ) -> CalendarIntegration:
        fields = body.changes
        if "name" in fields and fields["name"] is not None:
            integration.name = fields["name"]
        if "credentials" in fields and fields["credentials"] is not None:
            integration.credentials_enc = encrypt_credentials(fields["credentials"])
        if "sync_interval" in fields and fields["sync_interval"] is not None:
            integration.sync_interval = fields["sync_interval"]
        if "capabilities" in fields and fields["capabilities"] is not None:
            integration.capabilities = fields["capabilities"]
        if "default_category" in fields:
            integration.default_category = fields["default_category"]
        if "delete_behavior" in fields and fields["delete_behavior"] is not None:
            integration.delete_behavior = fields["delete_behavior"]

        integration.updated_at = datetime.now(UTC)
        await self._repo.save(integration)
        return integration
