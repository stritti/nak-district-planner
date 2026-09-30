"""Celery entry point for event-driven mail hooks."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any

from app.celery_app import celery


@celery.task(name="dispatch_event_mail_hooks")
def dispatch_event_mail_hooks(event_data: dict[str, Any]) -> dict[str, int]:
    from app.adapters.db.repositories.event_mail_hook import (
        SqlEventMailHookRepository,
        SqlRecipientDirectory,
    )
    from app.adapters.db.session import AsyncSessionLocal
    from app.adapters.mail import create_mail_service
    from app.application.event_mail_hooks import EventMailHookDispatcher, deserialize_event
    from app.application.tasks import _run_as_system_worker

    event = deserialize_event(event_data)

    async def _run() -> dict[str, int]:
        async with AsyncSessionLocal() as session:
            dispatcher = EventMailHookDispatcher(
                hooks=SqlEventMailHookRepository(session),
                recipients=SqlRecipientDirectory(session),
                mail_service=create_mail_service(),
            )
            return asdict(await dispatcher.dispatch(event))

    return asyncio.run(_run_as_system_worker(_run()))
