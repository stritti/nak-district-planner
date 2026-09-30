"""Typed constructors for domain events emitted by the application.

Each constructor produces exactly the placeholders declared for its event type
in ``EVENT_PLACEHOLDERS`` (``district_name`` is added at dispatch time), so
emitters cannot drift from the template contract.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.domain.events import DomainEvent, EventType

GERMAN_MONTHS = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


def external_event_detected(
    district_id: UUID, *, event_title: str, event_date: date, source: str
) -> DomainEvent:
    return DomainEvent(
        EventType.EXTERNAL_EVENT_DETECTED,
        district_id,
        {"event_title": event_title, "event_date": event_date.isoformat(), "source": source},
    )


def registration_received(
    district_id: UUID, *, leader_name: str, leader_email: str | None
) -> DomainEvent:
    return DomainEvent(
        EventType.REGISTRATION_RECEIVED,
        district_id,
        {"leader_name": leader_name, "leader_email": leader_email or ""},
    )


def assignment_confirmed(
    district_id: UUID, *, leader_name: str, event_title: str, event_date: date
) -> DomainEvent:
    return DomainEvent(
        EventType.ASSIGNMENT_CONFIRMED,
        district_id,
        {
            "leader_name": leader_name,
            "event_title": event_title,
            "event_date": event_date.isoformat(),
        },
    )


def plan_finalized(district_id: UUID, *, year: int, month: int) -> DomainEvent:
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1..12, got {month}")
    return DomainEvent(
        EventType.PLAN_FINALIZED,
        district_id,
        {"month": GERMAN_MONTHS[month - 1], "year": str(year)},
    )
