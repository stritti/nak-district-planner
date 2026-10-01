"""app/celery_app.py: Module."""

from celery import Celery
from celery.schedules import crontab, timedelta

from app.adapters.db.session import engine
from app.config import settings
from app.telemetry import setup_telemetry


def _make_sync_db_url(async_url: str) -> str:
    """Convert an asyncpg database URL to a psycopg2 sync URL for Celery."""
    prefix = "postgresql+asyncpg://"
    if not async_url.startswith(prefix):
        raise ValueError(
            f"DATABASE_URL must start with '{prefix}' for Celery broker derivation "
            f"(got scheme: {async_url.split('://')[0]!r})"
        )
    return "postgresql+psycopg2://" + async_url[len(prefix) :]


_sync_db_url = _make_sync_db_url(settings.database_url)

celery = Celery(
    "nak_planner",
    broker=f"sqla+{_sync_db_url}",
    backend=f"db+{_sync_db_url}",
    include=[
        "app.application.tasks",
        "app.application.reminder_tasks",
        "app.application.event_mail_hook_tasks",
        "app.application.slot_gap_tasks",
    ],
)

celery.conf.update(
    task_serializer="json",
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

