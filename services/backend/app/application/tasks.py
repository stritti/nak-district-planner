"""Celery tasks for calendar synchronisation (UC-02).

Tasks intentionally run synchronous Celery workers; asyncio.run() bridges
to the async database/HTTP layer.  This is the standard pattern for Celery
+ SQLAlchemy async without a dedicated async worker library.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="sync_calendar_integration", bind=True, max_retries=3, default_retry_delay=60)
def sync_calendar_integration(self, integration_id: str) -> dict:
    """Sync a single CalendarIntegration by ID.

    Returns a summary dict: {"created": int, "updated": int, "cancelled": int}
    """
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.sync_service import run_sync

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            result = await run_sync(uuid.UUID(integration_id), session)
            await session.commit()
            return result

    try:
        summary = asyncio.run(_run())
        logger.info("Sync %s completed: %s", integration_id, summary)
        return summary
    except Exception as exc:
        logger.exception("Sync %s failed: %s", integration_id, exc)
        raise self.retry(exc=exc)


@celery.task(name="sync_all_active_integrations")
def sync_all_active_integrations() -> dict:
    """Triggered by Celery beat every 5 minutes.

    Iterates all active integrations, skips those synced more recently than
    their configured sync_interval, and dispatches individual sync tasks.
    """
    from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
    from app.adapters.db.session import AsyncSessionLocal

    async def _get_due() -> list[str]:
        async with AsyncSessionLocal() as session:
            repo = SqlCalendarIntegrationRepository(session)
            integrations = await repo.list_active()
            now = datetime.now(timezone.utc)
            due = []
            for integration in integrations:
                if integration.last_synced_at is None:
                    due.append(str(integration.id))
                    continue
                elapsed = (now - integration.last_synced_at).total_seconds() / 60
                if elapsed >= integration.sync_interval:
                    due.append(str(integration.id))
            return due

    due_ids = asyncio.run(_get_due())
    for integration_id in due_ids:
        sync_calendar_integration.delay(integration_id)

    logger.info("Dispatched sync for %d integration(s)", len(due_ids))
    return {"dispatched": len(due_ids)}
