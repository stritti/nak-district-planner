# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Event-driven mail hooks: the HookEvaluator and its wiring to the event bus.

Bus handlers run synchronously inside the emitting request or task, while
hook lookup and SMTP delivery are async and slow. The bus handler therefore
only enqueues a Celery task (see ``event_mail_hook_tasks``);
``EventMailHookDispatcher`` does the work in the worker. The dispatcher has no
access to the event bus, so sending mail can never emit further events.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.application.event_template_renderer import render_event_template
from app.domain.events import DomainEvent, EventType
from app.domain.models.event_mail_hook import EventMailHook
from app.domain.ports.event_mail_hooks import EventMailHookRepository, RecipientDirectory
from app.domain.ports.mail import MailDeliveryError, MailService

logger = logging.getLogger(__name__)


@dataclass
class DispatchSummary:
    hooks: int = 0
    sent: int = 0
    skipped: int = 0
    failed: int = 0


class EventMailHookDispatcher:
    """HookEvaluator: send one mail per recipient for every active matching hook."""

    def __init__(
        self,
        hooks: EventMailHookRepository,
        recipients: RecipientDirectory,
        mail_service: MailService,
    ) -> None:
        self._hooks = hooks
        self._recipients = recipients
        self._mail = mail_service

    async def dispatch(self, event: DomainEvent) -> DispatchSummary:
        summary = DispatchSummary()
        hooks = await self._hooks.list_active(event.district_id, event.event_type)
        summary.hooks = len(hooks)
        if not hooks:
            return summary
        district_name = await self._recipients.district_name(event.district_id)
        if district_name is None:
            summary.skipped = len(hooks)
            return summary
        # The district name is authoritative; emitters need not supply it.
        payload = {**event.payload, "district_name": district_name}
        for hook in hooks:
            await self._send(hook, event.event_type, payload, summary)
        logger.info(
            "Event mail hooks dispatched: event_type=%s district_id=%s summary=%s",
            event.event_type,
            event.district_id,
            summary,
        )
        return summary

    async def _send(
        self,
        hook: EventMailHook,
        event_type: EventType,
        payload: Mapping[str, Any],
        summary: DispatchSummary,
    ) -> None:
        recipients = await self._recipients.emails_for_role(hook.district_id, hook.recipient_role)
        if not recipients:
            summary.skipped += 1
            return
        subject = _single_line(render_event_template(event_type, hook.subject_template, payload))
        body = render_event_template(event_type, hook.body_template, payload)
        for recipient in recipients:
            try:
                self._mail.send([recipient], subject, body)
            except MailDeliveryError:
                # At most once: a failed or uncertain SMTP delivery is not retried.
                logger.exception("Event mail hook delivery failed: hook_id=%s", hook.id)
                summary.failed += 1
            else:
                summary.sent += 1


def _single_line(text: str) -> str:
    """Payload values (e.g. registrant names) must not break the subject header."""
    return " ".join(text.split())


# ── Serialisation for the Celery boundary ────────────────────────────────────


def serialize_event(event: DomainEvent) -> dict[str, Any]:
    return {
        "event_type": event.event_type.value,
        "district_id": str(event.district_id),
        "payload": {
            key: None if value is None else str(value) for key, value in event.payload.items()
        },
        "occurred_at": event.occurred_at.isoformat(),
    }


def deserialize_event(data: Mapping[str, Any]) -> DomainEvent:
    return DomainEvent(
        event_type=EventType(data["event_type"]),
        district_id=UUID(data["district_id"]),
        payload=dict(data["payload"]),
        occurred_at=datetime.fromisoformat(data["occurred_at"]),
    )
