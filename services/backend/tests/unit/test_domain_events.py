"""Regression coverage for process-local domain events."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.events import DomainEvent, DomainEventBus, EventType


def test_event_timestamp_is_timezone_aware() -> None:
    event = DomainEvent(EventType.SYNC_ERROR, uuid4(), {})
    assert event.occurred_at.tzinfo == UTC
    assert event.occurred_at <= datetime.now(UTC)


def test_emit_notifies_multiple_subscribers_in_order() -> None:
    bus = DomainEventBus()
    observed: list[str] = []
    bus.subscribe(EventType.SYNC_ERROR, lambda _: observed.append("first"))
    bus.subscribe(EventType.SYNC_ERROR, lambda _: observed.append("second"))
    bus.emit(DomainEvent(EventType.SYNC_ERROR, uuid4(), {}))
    assert observed == ["first", "second"]


def test_other_event_types_do_not_receive_event() -> None:
    bus = DomainEventBus()
    observed = []
    bus.subscribe(EventType.SLOT_UNASSIGNED, observed.append)
    bus.emit(DomainEvent(EventType.SYNC_ERROR, uuid4(), {}))
    assert observed == []


def test_duplicate_subscription_and_unsubscribe() -> None:
    bus = DomainEventBus()
    observed = []
    bus.subscribe(EventType.SYNC_ERROR, observed.append)
    bus.subscribe(EventType.SYNC_ERROR, observed.append)
    event = DomainEvent(EventType.SYNC_ERROR, uuid4(), {})
    bus.emit(event)
    assert observed == [event]
    bus.unsubscribe(EventType.SYNC_ERROR, observed.append)
    bus.emit(event)
    assert observed == [event]
    bus.unsubscribe(EventType.SYNC_ERROR, observed.append)


def test_subscription_changes_during_emit_do_not_skip_handlers() -> None:
    bus = DomainEventBus()
    observed: list[str] = []

    def first(_: DomainEvent) -> None:
        observed.append("first")
        bus.unsubscribe(EventType.SYNC_ERROR, second)

    def second(_: DomainEvent) -> None:
        observed.append("second")

    bus.subscribe(EventType.SYNC_ERROR, first)
    bus.subscribe(EventType.SYNC_ERROR, second)
    bus.emit(DomainEvent(EventType.SYNC_ERROR, uuid4(), {}))
    assert observed == ["first", "second"]


def test_handler_failure_is_propagated() -> None:
    bus = DomainEventBus()

    def fail(_: DomainEvent) -> None:
        raise RuntimeError("handler failed")

    bus.subscribe(EventType.SYNC_ERROR, fail)
    with pytest.raises(RuntimeError, match="handler failed"):
        bus.emit(DomainEvent(EventType.SYNC_ERROR, uuid4(), {}))
