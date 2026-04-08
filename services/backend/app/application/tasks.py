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

    Returns a summary dict: {"dispatched": int}
    """
    from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
    from app.adapters.db.session import AsyncSessionLocal

    async def _run() -> list[str]:
        async with AsyncSessionLocal() as session:
            repo = SqlCalendarIntegrationRepository(session)
            integrations = await repo.list_active()
            now = datetime.now(timezone.utc)
            ids_to_sync: list[str] = []
            for integration in integrations:
                integration_id = str(integration.id)
                if integration.last_synced_at is None:
                    ids_to_sync.append(integration_id)
                    continue
                elapsed = (now - integration.last_synced_at).total_seconds() / 60
                if elapsed >= integration.sync_interval:
                    ids_to_sync.append(integration_id)
            return ids_to_sync

    ids = asyncio.run(_run())
    for integration_id in ids:
        sync_calendar_integration.delay(integration_id)
    logger.info("Dispatched sync for %d integration(s)", len(ids))
    return {"dispatched": len(ids)}


@celery.task(name="cleanup_old_events")
def cleanup_old_events() -> dict:
    """Delete events older than 24 months.

    Runs on the 1st of each month via Celery beat.  All events whose *end_at*
    is before the cutoff (now − 24 months) are permanently removed.
    """
    from app.adapters.db.repositories.event import SqlEventRepository
    from app.adapters.db.session import AsyncSessionLocal

    async def _run() -> dict:
        now = datetime.now(timezone.utc)
        # Compute cutoff as exactly 24 months (2 years) ago.
        # Handle the Feb-29 edge case: replace day with 28 when the target
        # year is not a leap year.
        try:
            cutoff = now.replace(year=now.year - 2)
        except ValueError:
            cutoff = now.replace(year=now.year - 2, day=28)

        async with AsyncSessionLocal() as session:
            repo = SqlEventRepository(session)
            deleted = await repo.delete_before(cutoff)
            await session.commit()

        return {"deleted": deleted, "cutoff": cutoff.isoformat()}

    result = asyncio.run(_run())
    logger.info(
        "cleanup_old_events: deleted %d event(s) older than %s",
        result["deleted"],
        result["cutoff"],
    )
    return result


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

    async def _run() -> dict:
        now = datetime.now(timezone.utc)
        years = {now.year}
        if now.month >= 9:  # September onwards → pre-import next year
            years.add(now.year + 1)

        total_created = total_updated = total_skipped = 0

        async with AsyncSessionLocal() as session:
            from app.application.feiertage_service import (
                import_feiertage,
                import_kirchliche_festtage,
            )

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
                        district_id=district.id,
                        year=year,
                        session=session,
                    )
                    total_created += r["created"]
                    total_updated += r["updated"]
                    total_skipped += r["skipped"]

            await session.commit()

        logger.info(
            "auto_import_feiertage: years=%s, districts=%d, created=%d, updated=%d, skipped=%d",
            sorted(years),
            len(all_districts),
            total_created,
            total_updated,
            total_skipped,
        )
        return {
            "years": sorted(years),
            "districts": len(all_districts),
            "created": total_created,
            "updated": total_updated,
            "skipped": total_skipped,
        }

    return asyncio.run(_run())


@celery.task(name="import_feiertage_task")
def import_feiertage_task(district_id: str, year: int, state_code: str | None = None) -> dict:
    """Import German public holidays for a district and year.

    Args:
        district_id: Target district UUID as string.
        year: Calendar year (e.g. 2026).
        state_code: 2-letter German state code (e.g. "BY") or None.

    Returns:
        dict with created/updated/skipped counts.
    """
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.feiertage_service import import_feiertage

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            result = await import_feiertage(
                district_id=uuid.UUID(district_id),
                year=year,
                state_code=state_code,
                session=session,
            )
            await session.commit()
            return result

    result = asyncio.run(_run())
    logger.info("import_feiertage_task: district=%s year=%d %s", district_id, year, result)
    return result


@celery.task(name="import_kirchliche_festtage_task")
def import_kirchliche_festtage_task(district_id: str, year: int) -> dict:
    """Import NAK kirchliche Festtage (Palmsonntag, Ostersonntag, Pfingstsonntag,
    Entschlafenen-Gottesdienste) for a district and year.

    Args:
        district_id: Target district UUID as string.
        year: Calendar year (e.g. 2026).

    Returns:
        dict with created/updated/skipped counts.
    """
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.feiertage_service import import_kirchliche_festtage

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            result = await import_kirchliche_festtage(
                district_id=uuid.UUID(district_id),
                year=year,
                session=session,
            )
            await session.commit()
            return result

    result = asyncio.run(_run())
    logger.info(
        "import_kirchliche_festtage_task: district=%s year=%d %s", district_id, year, result
    )
    return result


@celery.task(name="generate_draft_services_window")
def generate_draft_services_window() -> dict:
    """Generate draft worship services for the rolling next 8 weeks.

    Safe to run repeatedly: generation is idempotent and does not recreate
    moved generated events because it keys by immutable slot identity.
    """
    from app.adapters.db.repositories.congregation import SqlCongregationRepository
    from app.adapters.db.repositories.district import SqlDistrictRepository
    from app.adapters.db.repositories.event import SqlEventRepository
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.draft_service_generation import GenerateDraftServicesUseCase

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            use_case = GenerateDraftServicesUseCase(
                district_repo=SqlDistrictRepository(session),
                congregation_repo=SqlCongregationRepository(session),
                event_repo=SqlEventRepository(session),
            )
            result = await use_case.run()
            await session.commit()
            return result

    result = asyncio.run(_run())
    logger.info(
        "generate_draft_services_window: districts=%d congregations=%d created=%d "
        "skipped_existing=%d adopted_existing=%d invalid_configurations=%d",
        result["districts"],
        result["congregations"],
        result["created"],
        result["skipped_existing"],
        result["adopted_existing"],
        result["invalid_configurations"],
    )
    return result
