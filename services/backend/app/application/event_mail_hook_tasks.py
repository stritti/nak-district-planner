"""Celery adapter for event-driven mail hooks: bus handler, wiring and task."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Any

from celery.signals import worker_init

from app.application.event_mail_hooks import (
    EventMailHookDispatcher,
    deserialize_event,
    serialize_event,
)
from app.celery_app import celery
from app.domain.events import DomainEvent, DomainEventBus, EventType, event_bus

logger = logging.getLogger(__name__)


@celery.task(name="dispatch_event_mail_hooks")
def dispatch_event_mail_hooks(event_data: dict[str, Any]) -> dict[str, int]:
    from app.adapters.db.repositories.event_mail_hook import (
        SqlEventMailHookRepository,
        SqlRecipientDirectory,
    )
    from app.adapters.db.session import AsyncSessionLocal
    from app.adapters.mail import create_mail_service
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


def enqueue_event_mail_dispatch(event: DomainEvent) -> None:
    """Bus handler: hand the event to the worker without blocking the emitter."""
    try:
        dispatch_event_mail_hooks.delay(serialize_event(event))
    except Exception:
        # An unavailable broker must not fail the business operation.
        logger.exception("Event mail hook dispatch could not be queued: %s", event.event_type)


def register_event_mail_hooks(bus: DomainEventBus = event_bus) -> None:
    """Subscribe the hook evaluator to every event type (idempotent)."""
    for event_type in EventType:
        bus.subscribe(event_type, enqueue_event_mail_dispatch)


@worker_init.connect
def _register_in_worker(**_: object) -> None:
    """Events emitted inside worker tasks (e.g. calendar sync) trigger mail hooks too."""
    register_event_mail_hooks()
