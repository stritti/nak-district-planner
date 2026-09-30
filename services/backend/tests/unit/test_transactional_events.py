"""publish_after_commit: events reach the bus only for committed work."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.adapters.db.transactional_events import publish_after_commit
from app.domain.events import DomainEvent, DomainEventBus, EventType


@pytest.fixture
def bus() -> tuple[DomainEventBus, list[DomainEvent]]:
    bus = DomainEventBus()
    received: list[DomainEvent] = []
    for event_type in EventType:
        bus.subscribe(event_type, received.append)
    return bus, received


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    with Session(engine) as session:
        yield session
    engine.dispose()


def _event(label: str = "x") -> DomainEvent:
    return DomainEvent(EventType.SYNC_ERROR, uuid.uuid4(), {"error_message": label})


def _open_transaction(session: Session) -> None:
    session.execute(text("SELECT 1"))


def test_event_is_published_after_commit_not_before(session, bus) -> None:
    bus, received = bus
    _open_transaction(session)
    event = _event()

    publish_after_commit(session, event, bus)
    assert received == []

    session.commit()
    assert received == [event]


def test_event_is_discarded_on_rollback(session, bus) -> None:
    bus, received = bus
    _open_transaction(session)
    publish_after_commit(session, _event(), bus)

    session.rollback()
    session.commit()

    assert received == []


def test_rolled_back_savepoint_discards_only_its_events(session, bus) -> None:
    bus, received = bus
    _open_transaction(session)
    outer = _event("outer")
    publish_after_commit(session, outer, bus)

    savepoint = session.begin_nested()
    publish_after_commit(session, _event("inner"), bus)
    savepoint.rollback()

    session.commit()
    assert received == [outer]


def test_released_savepoint_publishes_with_outer_commit(session, bus) -> None:
    bus, received = bus
    _open_transaction(session)
    with session.begin_nested():
        inner = _event("inner")
        publish_after_commit(session, inner, bus)
    assert received == []

    session.commit()
    assert received == [inner]


def test_events_are_published_once(session, bus) -> None:
    bus, received = bus
    _open_transaction(session)
    publish_after_commit(session, _event(), bus)
    session.commit()
    _open_transaction(session)
    session.commit()

    assert len(received) == 1


def test_without_open_transaction_event_is_published_immediately(session, bus) -> None:
    bus, received = bus
    event = _event()
    publish_after_commit(session, event, bus)
    assert received == [event]


def test_async_session_is_unwrapped(bus) -> None:
    bus, received = bus
    event = _event()
    publish_after_commit(AsyncSession(), event, bus)  # no transaction begun
    assert received == [event]


def test_test_double_session_drops_event(bus) -> None:
    bus, received = bus
    publish_after_commit(AsyncMock(), _event(), bus)
    assert received == []


def test_failing_handler_does_not_break_commit(session, caplog) -> None:
    bus = DomainEventBus()

    def fail(_: DomainEvent) -> None:
        raise RuntimeError("handler down")

    bus.subscribe(EventType.SYNC_ERROR, fail)
    _open_transaction(session)
    publish_after_commit(session, _event(), bus)

    session.commit()  # must not raise

    assert "Domain event handler failed" in caplog.text
