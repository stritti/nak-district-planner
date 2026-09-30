"""Process-local domain events.

Subscribers are synchronous and isolated where appropriate. A durable outbox is
required before providing delivery guarantees across worker processes.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class EventType(StrEnum):
    SLOT_UNASSIGNED = "SLOT_UNASSIGNED"
    EXTERNAL_EVENT_DETECTED = "EXTERNAL_EVENT_DETECTED"
    SYNC_ERROR = "SYNC_ERROR"
    REGISTRATION_RECEIVED = "REGISTRATION_RECEIVED"
    ASSIGNMENT_CONFIRMED = "ASSIGNMENT_CONFIRMED"
    PLAN_FINALIZED = "PLAN_FINALIZED"


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: EventType
    district_id: UUID
    payload: Mapping[str, Any]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


EventHandler = Callable[[DomainEvent], None]


class DomainEventBus:
    """An explicit, testable observer with idempotent registration.

    Handlers run in subscription order. A handler failure propagates to the
    caller; producers must choose an appropriate post-commit failure policy.
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def emit(self, event: DomainEvent) -> None:
        for handler in tuple(self._handlers.get(event.event_type, ())):
            handler(event)


# Process-local instance; application startup owns its subscriptions.
event_bus = DomainEventBus()
