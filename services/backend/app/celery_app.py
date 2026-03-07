import os

from celery import Celery
from celery.schedules import timedelta

celery = Celery(
    "nak_planner",
    broker=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
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
        }
    },
)
