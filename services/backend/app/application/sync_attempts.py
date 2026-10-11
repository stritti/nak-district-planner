# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Durable calendar sync attempt tracking across HTTP and Celery entry points."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
from app.adapters.db.session import AsyncSessionLocal


async def record_sync_attempt(integration_id: uuid.UUID, error: str | None = None) -> None:
    """Commit attempt metadata in its own transaction after failed sync rollback.

    Callers must not pass provider-controlled messages: exception class names and
    curated constant strings are safe; URLs, HTTP response bodies and tokens are not.
    """
    async with AsyncSessionLocal() as session:
        repo = SqlCalendarIntegrationRepository(session)
        integration = await repo.get(integration_id)
        if integration is None:
            return
        integration.last_attempt_at = datetime.now(UTC)
        if error is not None:
            integration.last_sync_error = error[:500]
        await repo.save(integration)
        await session.commit()
