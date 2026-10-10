"""Celery tasks for calendar synchronisation (UC-02) and system maintenance.

IMPORTANT — async bridge pattern
=================================
Celery workers execute synchronous task functions.  To call async database/HTTP
code from a sync task, we use ``asyncio.run()`` inside each task function.
This is the standard, documented pattern for Celery + SQLAlchemy async without
a dedicated async Celery worker library.

Each task follows the same structure::

    @celery.task(...)
    def my_task(...) -> dict:
        async def _run() -> dict:
            async with AsyncSessionLocal() as session:
                ...  # async work here
                return result

        return asyncio.run(_run())

The ``_run()`` inner coroutine keeps the async logic isolated and testable
independently of Celery.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable
from datetime import UTC, date, datetime

from app.celery_app import celery
from app.domain.errors import IntegrationNotFoundError, UnsupportedCalendarTypeError
from app.domain.models.calendar_integration import SUPPORTED_CALENDAR_TYPES

logger = logging.getLogger(__name__)


async def _run_as_system_worker[T](coro: Awaitable[T]) -> T:
    """Run DB work with a bounded system-worker tenant context for RLS GUCs.

    Every task runs in its own ``asyncio.run`` loop. Pooled asyncpg connections
    are bound to the loop that opened them, so the pool is disposed before the
    loop closes; the next task opens fresh connections on its own loop (#464).
    """
    from app.adapters.db.session import engine
    from app.tenant import TenantContext

    TenantContext.set_context(user_sub="system:celery-worker", user_roles=["SYSTEM_WORKER"])
    try:
        return await coro
    finally:
        TenantContext.clear_context()
        await engine.dispose()


# Exponential backoff for failing syncs: 60 s, 120 s, 240 s, 480 s (capped at
# one hour) with full jitter so simultaneous failures do not retry in lockstep.
SYNC_MAX_RETRIES = 4
SYNC_RETRY_BACKOFF_SECONDS = 60
SYNC_RETRY_BACKOFF_MAX_SECONDS = 3600


def _integration_id_from(args: tuple, kwargs: dict) -> str | None:
    return args[0] if args else kwargs.get("integration_id")


def _sync_failure_context(integration_id: str | None, exc: BaseException, attempt: int) -> dict:
    """Structured log fields; exception text is omitted as it may carry provider data."""
    return {
        "integration_id": integration_id,
        "error_class": type(exc).__name__,
        "attempt": attempt,
    }


async def _alert_sync_failure(integration_id: str, exc: BaseException, attempts: int) -> None:
    from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
    from app.adapters.db.repositories.notification import SqlNotificationRepository
    from app.adapters.db.session import AsyncSessionLocal
    from app.adapters.db.transactional_events import publish_after_commit
    from app.application.sync_failure_alerts import SyncFailure, SyncFailureAlerter

    async with AsyncSessionLocal() as session:
        alerter = SyncFailureAlerter(
            integrations=SqlCalendarIntegrationRepository(session),
            notifications=SqlNotificationRepository(session),
            publish=lambda event: publish_after_commit(session, event),
        )
        failure = SyncFailure(
            integration_id=uuid.UUID(integration_id),
            error_class=type(exc).__name__,
            attempts=attempts,
        )
        if await alerter.alert(failure) is not None:
            await session.commit()


class SyncIntegrationTask(celery.Task):
    """Celery hooks that log each failed attempt and alert once retries are exhausted."""

    def on_retry(self, exc, task_id, args, kwargs, einfo) -> None:
        context = _sync_failure_context(
            _integration_id_from(args, kwargs), exc, self.request.retries + 1
        )
        logger.warning(
            "Calendar sync attempt failed, retrying: integration_id=%s error_class=%s attempt=%d",
            context["integration_id"],
            context["error_class"],
            context["attempt"],
            extra=context,
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:
        integration_id = _integration_id_from(args, kwargs)
        context = _sync_failure_context(integration_id, exc, self.request.retries + 1)
        logger.error(
            "Calendar sync failed permanently: integration_id=%s error_class=%s attempt=%d",
            context["integration_id"],
            context["error_class"],
            context["attempt"],
            extra=context,
        )
        if integration_id is None:
            return
        try:
            asyncio.run(
                _run_as_system_worker(_alert_sync_failure(integration_id, exc, context["attempt"]))
            )
        except Exception:
            # Alerting must never mask the original failure.
            logger.exception(
                "Sync failure alert could not be created: integration_id=%s", integration_id
            )


@celery.task(
    name="sync_calendar_integration",
    base=SyncIntegrationTask,
    bind=True,
    autoretry_for=(Exception,),
    dont_autoretry_for=(IntegrationNotFoundError, UnsupportedCalendarTypeError),
    max_retries=SYNC_MAX_RETRIES,
    retry_backoff=SYNC_RETRY_BACKOFF_SECONDS,
    retry_backoff_max=SYNC_RETRY_BACKOFF_MAX_SECONDS,
    retry_jitter=True,
)
def sync_calendar_integration(self, integration_id: str) -> dict:
    """Sync a single CalendarIntegration by ID.

    Failures are retried with exponential backoff (see ``SYNC_*`` constants);
    ``SyncIntegrationTask`` logs every failed attempt and alerts after the last.

    Returns a dict with ``created``, ``updated``, ``cancelled``, ``auto_matched`` counts.
    """
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.sync_service import run_sync

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            result = await run_sync(uuid.UUID(integration_id), session)
            await session.commit()
            return {
                "created": result.created,
                "updated": result.updated,
                "cancelled": result.cancelled,
                "auto_matched": result.auto_matched,
                "skipped": result.skipped,
                "failed": result.failed,
            }

    summary = asyncio.run(_run_as_system_worker(_run()))
    logger.info("Sync %s completed: %s", integration_id, summary)
    return summary


def _due_integration_ids(integrations, now: datetime) -> list[str]:
    """Return ids of integrations due for sync; unsupported providers are skipped (#467)."""
    ids: list[str] = []
    for integration in integrations:
        if integration.type not in SUPPORTED_CALENDAR_TYPES:
            logger.warning(
                "Automatischer Sync übersprungen: Kalendertyp %s wird in Version 1.0 "
                "nicht unterstützt (integration_id=%s)",
                integration.type,
                integration.id,
            )
            continue
        if integration.last_synced_at is None:
            ids.append(str(integration.id))
            continue
        elapsed = (now - integration.last_synced_at).total_seconds() / 60
        if elapsed >= integration.sync_interval:
            ids.append(str(integration.id))
    return ids


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
            return _due_integration_ids(await repo.list_active(), datetime.now(UTC))

    ids = asyncio.run(_run_as_system_worker(_run()))
    for integration_id in ids:
        sync_calendar_integration.delay(integration_id)  # type: ignore[attr-defined]
    logger.info("Dispatched sync for %d integration(s)", len(ids))
    return {"dispatched": len(ids)}


def _unreleased_retention_conditions(cutoff_date: date):
    """Shared conditions for identifying drafts eligible for retention."""
    from sqlalchemy import or_

    from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
    from app.domain.models.planning_slot import EventApprovalStatus

    return (
        PlanningSlotORM.planning_date < cutoff_date,
        PlanningSlotORM.released_at.is_(None),
        or_(
            PlanningSlotORM.approval_status.is_(None),
            PlanningSlotORM.approval_status != EventApprovalStatus.CONFIRMED,
        ),
    )


def _unreleased_retention_statement(cutoff_date: date):
    """Retain the set-based predicate for integration and policy checks."""
    from sqlalchemy import delete

    from app.adapters.db.orm_models.planning_slot import PlanningSlotORM

    return delete(PlanningSlotORM).where(*_unreleased_retention_conditions(cutoff_date))


async def _delete_expired_drafts(session, cutoff_date: date) -> int:
    """Delete eligible slots via aggregate cleanup, not a raw bulk DELETE.

    Linked invitations and target copies are reconciled by the repository;
    a concurrent publication is skipped without failing the monthly job.
    """
    from sqlalchemy import select

    from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
    from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
    from app.domain.models.planning_slot import ReleasedEventError

    rows = await session.execute(
        select(PlanningSlotORM.id)
        .where(*_unreleased_retention_conditions(cutoff_date))
        .order_by(PlanningSlotORM.id)
    )
    repo = SqlPlanningSlotRepository(session)
    deleted = 0
    for slot_id in rows.scalars().all():
        try:
            deleted += int(await repo.delete(slot_id))
        except ReleasedEventError:
            # A candidate can be confirmed after the initial select.
            continue
    return deleted


@celery.task(name="cleanup_old_events")
def cleanup_old_events() -> dict:
    """Delete *never-released* events older than 24 months.

    Released and cancelled events retain their stable identifiers indefinitely.
    The retention job runs monthly via Celery beat.
    """
    from app.adapters.db.session import AsyncSessionLocal

    async def _run() -> dict:
        now = datetime.now(UTC)
        # Compute cutoff as exactly 24 months (2 years) ago.
        # Handle the Feb-29 edge case: replace day with 28 when the target
        # year is not a leap year.
        try:
            cutoff = now.replace(year=now.year - 2)
        except ValueError:
            cutoff = now.replace(year=now.year - 2, day=28)

        async with AsyncSessionLocal() as session:
            # PlanningSlot uses planning_date (date), not end_at (datetime).
            # Delete slots with planning_date before cutoff date.
            cutoff_date = cutoff.date()
            from sqlalchemy import insert

            from app.adapters.db.domain_audit import bulk_delete_audit_row
            from app.adapters.db.orm_models.audit_log import AuditLogORM

            deleted = await _delete_expired_drafts(session, cutoff_date)
            if deleted:
                await session.execute(
                    insert(AuditLogORM.__table__),
                    [
                        bulk_delete_audit_row(
                            "planning_slot",
                            deleted=deleted,
                            reason="retention",
                            criteria={"planning_date_before": cutoff_date},
                        )
                    ],
                )
            await session.commit()

        return {"deleted": deleted, "cutoff": cutoff.isoformat()}

    result = asyncio.run(_run_as_system_worker(_run()))
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
    from datetime import datetime

    from app.adapters.db.repositories.district import SqlDistrictRepository
    from app.adapters.db.session import AsyncSessionLocal

    async def _run() -> dict:
        now = datetime.now(UTC)
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

    return asyncio.run(_run_as_system_worker(_run()))


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

    result = asyncio.run(_run_as_system_worker(_run()))
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

    result = asyncio.run(_run_as_system_worker(_run()))
    logger.info(
        "import_kirchliche_festtage_task: district=%s year=%d %s", district_id, year, result
    )
    return result


@celery.task(name="generate_draft_services_window")
def generate_draft_services_window() -> dict:
    """Generate draft worship services for the rolling next 8 weeks.

    Generates PlanningSlot + EventInstance from congregation service_times.
    Safe to run repeatedly: generation is idempotent.
    """
    from app.adapters.db.repositories.congregation import SqlCongregationRepository
    from app.adapters.db.repositories.district import SqlDistrictRepository
    from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
    from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.draft_service_generation import GenerateDraftServicesUseCase

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            use_case = GenerateDraftServicesUseCase(
                district_repo=SqlDistrictRepository(session),
                congregation_repo=SqlCongregationRepository(session),
                slot_repo=SqlPlanningSlotRepository(session),
                instance_repo=SqlEventInstanceRepository(session),
            )
            result = await use_case.run()
            await session.commit()
            return result

    result = asyncio.run(_run_as_system_worker(_run()))
    logger.info(
        "generate_draft_services_window: districts=%d congregations=%d created=%d skipped=%d",
        result["districts"],
        result["congregations"],
        result["created"],
        result["skipped_existing"],
    )
    return result


@celery.task(name="generate_planning_series_slots")
def generate_planning_series_slots() -> dict:
    """Generate PlanningSlot + EventInstance from active PlanningSeries.

    Runs daily to keep a rolling 12-month window of generated slots.
    Safe to run repeatedly: skips existing slots by (series_id, date, congregation).
    """
    from app.adapters.db.repositories.congregation import SqlCongregationRepository
    from app.adapters.db.repositories.district import SqlDistrictRepository
    from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
    from app.adapters.db.repositories.planning_series import SqlPlanningSeriesRepository
    from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.planning_series_generator import PlanningSeriesGenerator
    from app.config import settings

    if not settings.use_series_generation:
        logger.info("generate_planning_series_slots: disabled via USE_SERIES_GENERATION=False")
        return {"status": "disabled"}

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            generator = PlanningSeriesGenerator(
                series_repo=SqlPlanningSeriesRepository(session),
                slot_repo=SqlPlanningSlotRepository(session),
                instance_repo=SqlEventInstanceRepository(session),
                district_repo=SqlDistrictRepository(session),
                congregation_repo=SqlCongregationRepository(session),
            )
            result = await generator.run()
            await session.commit()
            return result

    result = asyncio.run(_run_as_system_worker(_run()))
    logger.info(
        "generate_planning_series_slots: series=%d created=%d skipped=%d",
        result["series_processed"],
        result["slots_created"],
        result["slots_skipped"],
    )
    return result


@celery.task(name="check_version")
def check_version() -> dict:
    """Celery beat task — runs every 6 hours.

    Queries ghcr.io for the latest backend image tag,
    caches the result, and returns it.
    """
    from app.adapters.version_check.cache import version_cache
    from app.adapters.version_check.ghcr import GhcrTagFetcher
    from app.config import settings

    current = settings.app_version
    latest = GhcrTagFetcher().fetch_latest_version("backend", current)
    version_cache.set(latest)
    logger.info("check_version: latest=%s current=%s", latest, current)
    return {"latest": latest}


@celery.task(name="generate_planning_slots")
def generate_planning_slots() -> dict:
    """Celery beat task — runs daily at 02:00 Europe/Berlin.

    Generates PlanningSlots from all active PlanningSeries for the next 6-12 months.
    This ensures that the matrix view always has up-to-date planning data.

    The task:
    - Processes all active PlanningSeries across all districts
    - Generates slots for the configured horizon (default: 6 months)
    - Skips existing slots (idempotent)
    - Logs results for monitoring
    """
    from app.adapters.db.repositories.planning_series import SqlPlanningSeriesRepository
    from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.planning_series_service import PlanningSeriesSlotGenerationService

    async def _run() -> dict:
        async with AsyncSessionLocal() as session:
            service = PlanningSeriesSlotGenerationService(
                series_repo=SqlPlanningSeriesRepository(session),
                slot_repo=SqlPlanningSlotRepository(session),
                default_horizon_months=6,
            )

            result = await service.generate_all_slots()
            await session.commit()

            return result

    result = asyncio.run(_run_as_system_worker(_run()))
    logger.info(
        "generate_planning_slots: generated=%d, skipped=%d, series_processed=%d, districts_processed=%d",
        result.get("generated", 0),
        result.get("skipped", 0),
        result.get("series_processed", 0),
        result.get("districts_processed", 0),
    )
    return result
