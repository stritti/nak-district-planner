"""Publish domain events only after the surrounding transaction commits.

Services record events while they write; the events reach the
``DomainEventBus`` once the outermost transaction commits. Events recorded
inside a savepoint that is rolled back, or in a transaction that is rolled back
as a whole, are discarded. This prevents notifications about changes that
never became visible.

This is not a durable outbox: events are lost if the process dies between
commit and publish.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, SessionTransaction

from app.domain.events import DomainEvent, DomainEventBus, event_bus

logger = logging.getLogger(__name__)

_PENDING_KEY = "pending_domain_events"


@dataclass(frozen=True, slots=True)
class _Pending:
    transaction: SessionTransaction
    event: DomainEvent
    bus: DomainEventBus


def publish_after_commit(
    session: AsyncSession | Session, event: DomainEvent, bus: DomainEventBus = event_bus
) -> None:
    """Queue ``event`` for publication when ``session`` commits."""
    sync_session = session.sync_session if isinstance(session, AsyncSession) else session
    if not isinstance(sync_session, Session):
        # Test doubles have no transaction that could ever commit.
        logger.debug("Domain event dropped for non-SQLAlchemy session: %s", event.event_type)
        return
    transaction = sync_session.get_nested_transaction() or sync_session.get_transaction()
    if transaction is None:
        # No open transaction: nothing can roll the change back any more.
        _emit(bus, event)
        return
    sync_session.info.setdefault(_PENDING_KEY, []).append(_Pending(transaction, event, bus))


def _emit(bus: DomainEventBus, event: DomainEvent) -> None:
    try:
        bus.emit(event)
    except Exception:
        # The data is already committed; a failing subscriber must not turn a
        # successful commit into an error for the caller.
        logger.exception("Domain event handler failed: event_type=%s", event.event_type)


def _within(transaction: SessionTransaction, rolled_back: SessionTransaction) -> bool:
    current: SessionTransaction | None = transaction
    while current is not None:
        if current is rolled_back:
            return True
        current = current.parent
    return False


@sa_event.listens_for(Session, "after_commit")
def _publish_pending(session: Session) -> None:
    if session.in_nested_transaction():
        # Released savepoint: the outer transaction can still roll back.
        return
    pending: list[_Pending] = session.info.pop(_PENDING_KEY, [])
    for item in pending:
        _emit(item.bus, item.event)


@sa_event.listens_for(Session, "after_soft_rollback")
def _discard_rolled_back(session: Session, previous_transaction: SessionTransaction) -> None:
    pending: list[_Pending] = session.info.get(_PENDING_KEY, [])
    kept = [item for item in pending if not _within(item.transaction, previous_transaction)]
    if kept:
        session.info[_PENDING_KEY] = kept
    else:
        session.info.pop(_PENDING_KEY, None)
