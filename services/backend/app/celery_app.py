# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/celery_app.py: Module."""

import asyncio
import logging

from celery import Celery, signals
from celery.schedules import crontab, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.db.schema_version import SchemaVersionError, assert_database_schema_current
from app.adapters.db.session import engine
from app.config import production_guard, settings
from app.telemetry import setup_telemetry

celery = Celery(
    "nak_planner",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.adapters.worker.tasks",
        "app.adapters.worker.reminder_tasks",
        "app.adapters.worker.event_mail_hook_tasks",
        "app.adapters.worker.slot_gap_tasks",
    ],
)

celery.conf.update(
    task_serializer="json",
    worker_prefetch_multiplier=1,
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Berlin",
    enable_utc=True,
    beat_schedule={
        "sync-all-active-calendars": {
            "task": "sync_all_active_integrations",
            "schedule": timedelta(minutes=5),
        },
        "auto-import-feiertage": {
            "task": "auto_import_feiertage",
            "schedule": crontab(day_of_month="1", hour="3", minute="0"),
        },
        "cleanup-old-events": {
            "task": "cleanup_old_events",
            "schedule": crontab(day_of_month="1", hour="2", minute="0"),
        },
        "generate-draft-services-window": {
            "task": "generate_draft_services_window",
            "schedule": crontab(hour="1", minute="10"),
        },
        "generate-planning-series-slots": {
            "task": "generate_planning_series_slots",
            "schedule": crontab(hour="1", minute="20"),
        },
        "check-version": {
            "task": "check_version",
            "schedule": crontab(minute="0", hour="*/6"),
        },
        # Hourly evaluation respects per-config time_of_day (within the hour).
        # The per-recipient delivery ledger makes overlapping checks idempotent.
        "check-due-reminders": {
            "task": "check_due_reminders",
            "schedule": crontab(minute="0"),
        },
        # After the nightly draft and series generation (01:10/01:20), so newly
        # generated slots are included; reports go out before the workday.
        "scan-slot-gaps": {
            "task": "scan_slot_gaps",
            "schedule": crontab(hour="6", minute="15"),
        },
    },
)

setup_telemetry(sqlalchemy_engine=engine)


async def assert_legacy_broker_drained(db_engine) -> None:
    """Fail closed if the deprecated SQL transport still holds messages."""
    async with db_engine.connect() as conn:
        exists = await conn.scalar(text("SELECT to_regclass('public.kombu_message') IS NOT NULL"))
        if exists and await conn.scalar(text("SELECT COUNT(*) FROM public.kombu_message")):
            raise SchemaVersionError(
                "Legacy SQL Celery broker has queued messages: drain the previous "
                "worker before switching to Valkey (see production runbook)."
            )


@signals.worker_init.connect
@signals.beat_init.connect
def assert_schema_current_on_startup(**_kwargs) -> None:
    """Refuse to start with an unsafe production config or a stale database schema.

    Celery logs and swallows ordinary exceptions from signal handlers, so a
    mismatch is raised as ``SystemExit`` to actually stop the process. A
    throwaway engine keeps pooled connections out of the forked pool workers.
    """

    try:
        production_guard(settings)
    except RuntimeError as exc:
        logging.getLogger(__name__).critical("Unsafe production configuration: %s", exc)
        raise SystemExit(1) from exc

    async def _check() -> None:
        check_engine = create_async_engine(settings.database_url, poolclass=NullPool)
        try:
            await assert_database_schema_current(check_engine)
            await assert_legacy_broker_drained(check_engine)
        finally:
            await check_engine.dispose()

    try:
        asyncio.run(_check())
    except SchemaVersionError as exc:
        logging.getLogger(__name__).critical("Database schema check failed: %s", exc)
        raise SystemExit(1) from exc
