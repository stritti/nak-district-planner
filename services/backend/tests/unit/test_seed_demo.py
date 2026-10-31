# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""The demo district shows each planning situation exactly where the scenario says."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import date

import pytest

from app.application.draft_service_generation import expand_service_slots
from app.domain.planning.duty_conflicts import ScheduledDuty
from app.domain.planning.matrix_conflicts import PlannedService, matrix_conflicts
from seed_demo import (
    DEMO_CONGREGATIONS,
    DEMO_LEADERS,
    DEMO_TIMEZONE,
    DEMO_WEEKS,
    ORGANIST_NAME,
    DemoService,
    plan_demo,
)

LEADER_IDS = {leader.name: uuid.uuid4() for leader in DEMO_LEADERS}
CONGREGATION_IDS = {name: uuid.uuid4() for name in DEMO_CONGREGATIONS}


def _services(monday: date) -> list[DemoService]:
    services = []
    for name, service_times in DEMO_CONGREGATIONS.items():
        for planned in expand_service_slots(
            service_times=service_times,
            from_date=monday,
            to_date_exclusive=date.fromordinal(monday.toordinal() + 7 * DEMO_WEEKS),
            timezone_name=DEMO_TIMEZONE,
        ):
            services.append(DemoService(uuid.uuid4(), name, planned.start_at_utc))
    return services


def _conflicts(services: list[DemoService], monday: date) -> dict[tuple[str, int], list[str]]:
    plan = plan_demo(services, monday=monday)
    by_slot = {service.slot_id: service for service in services}
    planned = [
        PlannedService(
            uuid.uuid4(),
            LEADER_IDS[plan.leaders[service.slot_id]],
            CONGREGATION_IDS[service.congregation],
            service.start_at,
            service.end_at,
            service.slot_id,
        )
        for service in services
        if service.slot_id in plan.leaders
    ]
    other_bookings: dict[uuid.UUID, list[ScheduledDuty]] = {}
    for slot_id, person in plan.organist_duties:
        if person in LEADER_IDS:
            duty = by_slot[slot_id]
            other_bookings.setdefault(LEADER_IDS[person], []).append(
                ScheduledDuty(slot_id, CONGREGATION_IDS[duty.congregation], duty.start_at,
                              duty.end_at, True)
            )
    absences = {
        LEADER_IDS[name]: [(start, end)] for name, start, end in plan.absences
    }
    found = matrix_conflicts(
        planned, min_travel_minutes=30, other_bookings=other_bookings, unavailability=absences
    )
    service_by_key = {item.key: by_slot[item.slot_id] for item in planned}
    return {
        (service_by_key[key].congregation, (service_by_key[key].start_at.date() - monday).days // 7):
        [conflict.rule_id for conflict in conflicts]
        for key, conflicts in found.items()
    }


@pytest.mark.parametrize("monday", [date(2026, 10, 26), date(2027, 3, 22), date(2026, 12, 28)])
def test_each_planning_situation_appears_once(monday: date) -> None:
    services = _services(monday)
    assert _conflicts(services, monday) == {
        ("Gallisches Dorf", 1): ["no_double_booking"],
        ("Babaorum", 1): ["no_double_booking"],
        ("Gallisches Dorf", 2): ["travel_time_check"],
        ("Aquarium", 2): ["travel_time_check"],
        ("Babaorum", 3): ["leader_available"],
        ("Laudanum", 4): ["no_double_booking"],
    }


def test_gaps_release_and_organist() -> None:
    monday = date(2026, 10, 26)
    services = _services(monday)
    plan = plan_demo(services, monday=monday)

    gaps = Counter(s.congregation for s in services if s.slot_id not in plan.leaders)
    assert gaps == Counter({"Aquarium": 1, "Laudanum": 1, "Gallisches Dorf": 1})
    # Six services a week (four Sundays, two weekday services); the first two weeks are released.
    assert len(services) == 6 * DEMO_WEEKS
    assert len(plan.confirmed) == 12
    assert [name for _, name in plan.organist_duties].count(ORGANIST_NAME) == DEMO_WEEKS
    assert set(plan.leaders.values()) <= set(LEADER_IDS)
