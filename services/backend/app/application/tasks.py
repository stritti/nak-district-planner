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


@celery.task(name="auto_import_feiertage")
def auto_import_feiertage() -> dict:
    """Celery beat task — runs on the 1st of each month at 03:00 Europe/Berlin.

    Imports German public holidays for:
    - the current year (ensures new districts are covered)
    - the upcoming year (starting from September, i.e. 4 months in advance)

    Only processes districts that have a state_code configured.
    Import is idempotent — safe to run multiple times.
    """
    from datetime import datetime, timezone

    from app.adapters.db.repositories.district import SqlDistrictRepository
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.feiertage_service import import_feiertage

    async def _run() -> dict:
        now = datetime.now(timezone.utc)
        years = {now.year}
        if now.month >= 9:  # September onwards → pre-import next year
            years.add(now.year + 1)

        total_created = total_updated = total_skipped = 0

        async with AsyncSessionLocal() as session:
            from app.application.feiertage_service import import_feiertage, import_kirchliche_festtage

            repo = SqlDistrictRepository(session)
            all_districts = await repo.list_all()

            for district in all_districts:
                for year in years:
                    # Gesetzliche Feiertage — nur für Bezirke mit konfiguriertem Bundesland
                    if district.state_code:
                        r = await import_feiertage(
                            district_id=district.id,
                            year=year,
                            state_code=district.state_code,
                            session=session,
                        )
                        total_created += r["created"]
                        total_updated += r["updated"]
                        total_skipped += r["skipped"]

                    # Kirchliche Festtage (Palmsonntag, Ostersonntag, Pfingstsonntag) — immer
                    r = await import_kirchliche_festtage(
                        district_id=district.id, year=year, session=session,
                    )
                    total_created += r["created"]
                    total_updated += r["updated"]
                    total_skipped += r["skipped"]

            await session.commit()

        logger.info(
            "auto_import_feiertage: years=%s, districts=%d, created=%d, updated=%d, skipped=%d",
            sorted(years), len(all_districts), total_created, total_updated, total_skipped,
        )
        return {
            "years": sorted(years),
            "districts": len(all_districts),
            "created": total_created,
            "updated": total_updated,
            "skipped": total_skipped,
        }

    return asyncio.run(_run())
