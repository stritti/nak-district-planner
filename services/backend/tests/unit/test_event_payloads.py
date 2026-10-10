# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Event constructors produce exactly the placeholders their templates may use."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.domain import event_payloads
from app.domain.events import EventType
from app.domain.models.event_mail_hook import EVENT_PLACEHOLDERS

DISTRICT = uuid.uuid4()

EVENTS = {
    EventType.EXTERNAL_EVENT_DETECTED: event_payloads.external_event_detected(
        DISTRICT, event_title="Konzert", event_date=date(2026, 12, 24), source="Gemeindekalender"
    ),
    EventType.REGISTRATION_RECEIVED: event_payloads.registration_received(
        DISTRICT, leader_name="Anna", leader_email=None
    ),
    EventType.ASSIGNMENT_CONFIRMED: event_payloads.assignment_confirmed(
        DISTRICT, leader_name="Anna", event_title="Gottesdienst", event_date=date(2026, 12, 24)
    ),
    EventType.PLAN_FINALIZED: event_payloads.plan_finalized(DISTRICT, year=2026, month=3),
}


@pytest.mark.parametrize("event_type", list(EVENTS))
def test_payload_matches_placeholder_contract(event_type: EventType) -> None:
    event = EVENTS[event_type]
    assert event.event_type == event_type
    assert event.district_id == DISTRICT
    assert set(event.payload) == EVENT_PLACEHOLDERS[event_type] - {"district_name"}
    assert all(isinstance(value, str) for value in event.payload.values())


def test_values_are_formatted_for_humans() -> None:
    assert EVENTS[EventType.PLAN_FINALIZED].payload == {"month": "März", "year": "2026"}
    assert EVENTS[EventType.ASSIGNMENT_CONFIRMED].payload["event_date"] == "2026-12-24"
    assert EVENTS[EventType.REGISTRATION_RECEIVED].payload["leader_email"] == ""


@pytest.mark.parametrize("month", [0, 13])
def test_plan_finalized_rejects_invalid_month(month: int) -> None:
    with pytest.raises(ValueError, match="month"):
        event_payloads.plan_finalized(DISTRICT, year=2026, month=month)
