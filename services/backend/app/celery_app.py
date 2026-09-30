"""app/celery_app.py: Module."""

from celery import Celery
from celery.schedules import crontab, timedelta
from celery.signals import worker_init

from app.adapters.db.session import engine
from app.application.event_mail_hooks import register_event_mail_hooks
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
    },
)

setup_telemetry(sqlalchemy_engine=engine)


@worker_init.connect
def _register_domain_event_handlers(**_: object) -> None:
    """Events emitted inside worker tasks (e.g. calendar sync) trigger mail hooks too."""
    register_event_mail_hooks()
