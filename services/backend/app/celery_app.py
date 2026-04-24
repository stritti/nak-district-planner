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
    include=["app.application.tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Berlin",
    enable_utc=True,
    # Beat schedule: kick off a "sync all active integrations" task every 5 minutes.
    # Individual integrations respect their own sync_interval; the task skips those
    # that were synced more recently than their configured interval.
    beat_schedule={
        "sync-all-active-calendars": {
            "task": "sync_all_active_integrations",
            "schedule": timedelta(minutes=5),
        },
        # 1st of each month at 03:00 Europe/Berlin — imports current year + next year from September
        "auto-import-feiertage": {
            "task": "auto_import_feiertage",
            "schedule": crontab(day_of_month="1", hour="3", minute="0"),
        },
        # 1st of each month at 02:00 Europe/Berlin — deletes events older than 24 months
        "cleanup-old-events": {
            "task": "cleanup_old_events",
            "schedule": crontab(day_of_month="1", hour="2", minute="0"),
        },
        # Daily at 01:10 Europe/Berlin — keep a rolling 8-week draft service window
        "generate-draft-services-window": {
            "task": "generate_draft_services_window",
            "schedule": crontab(hour="1", minute="10"),
        },
    },
)

setup_telemetry(sqlalchemy_engine=engine)
