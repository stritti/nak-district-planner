# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Conflicts shown in the matrix: double booking, travel time and absences per leader."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.domain.planning.conflict_result import Severity
from app.domain.planning.duty_conflicts import ScheduledDuty
from app.domain.planning.matrix_conflicts import PlannedService, matrix_conflicts

START = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
LEADER, OTHER_LEADER = uuid.uuid4(), uuid.uuid4()
NORD, SUED = uuid.uuid4(), uuid.uuid4()


def _service(offset_minutes, *, leader=LEADER, congregation=NORD, minutes=90) -> PlannedService:
    start = START + timedelta(minutes=offset_minutes)
    return PlannedService(uuid.uuid4(), leader, congregation, start, start + timedelta(minutes=minutes))


def test_a_lone_assignment_has_no_conflict() -> None:
    assert matrix_conflicts([_service(0)], min_travel_minutes=30) == {}


def test_overlapping_assignments_of_one_leader_block_both_cells() -> None:
    a, b = _service(0), _service(30, congregation=SUED)
    result = matrix_conflicts([a, b], min_travel_minutes=30)
    for service in (a, b):
        [conflict] = result[service.key]
        assert conflict.severity == Severity.BLOCK and conflict.rule_id == "no_double_booking"


def test_short_travel_time_between_congregations_warns_both_cells() -> None:
    a, b = _service(0, congregation=NORD), _service(100, congregation=SUED)  # 10 min gap
    result = matrix_conflicts([a, b], min_travel_minutes=30)
    for service in (a, b):
        [conflict] = result[service.key]
        assert conflict.severity == Severity.WARN and conflict.rule_id == "travel_time_check"


def test_enough_travel_time_or_the_same_congregation_is_fine() -> None:
    a = _service(0, congregation=NORD)
    far = _service(130, congregation=SUED)  # 40 min gap
    near_same = _service(100, congregation=NORD)  # 10 min gap, same congregation
    assert matrix_conflicts([a, far], min_travel_minutes=30) == {}
    assert matrix_conflicts([a, near_same], min_travel_minutes=30) == {}


def test_different_leaders_never_conflict() -> None:
    a, b = _service(0), _service(0, leader=OTHER_LEADER)
    assert matrix_conflicts([a, b], min_travel_minutes=30) == {}


def test_a_leader_with_three_services_flags_only_the_involved_ones() -> None:
    a, b, free = _service(0), _service(30, congregation=SUED), _service(600)
    result = matrix_conflicts([a, b, free], min_travel_minutes=30)
    assert set(result) == {a.key, b.key}


def _duty(offset_minutes, *, congregation=SUED, minutes=60, slot_id=None) -> ScheduledDuty:
    start = START + timedelta(minutes=offset_minutes)
    return ScheduledDuty(
        slot_id or uuid.uuid4(), congregation, start, start + timedelta(minutes=minutes),
        strong=True,
    )


def test_a_duty_of_the_same_person_elsewhere_blocks_the_service() -> None:
    service = _service(0)
    result = matrix_conflicts(
        [service], min_travel_minutes=30, other_bookings={LEADER: [_duty(30)]},
    )
    [conflict] = result[service.key]
    assert conflict.severity == Severity.BLOCK and conflict.rule_id == "no_double_booking"


def test_a_duty_shortly_after_in_another_congregation_warns() -> None:
    service = _service(0)  # ends at 10:30
    result = matrix_conflicts(
        [service], min_travel_minutes=30, other_bookings={LEADER: [_duty(100)]},
    )
    [conflict] = result[service.key]
    assert conflict.severity == Severity.WARN and conflict.rule_id == "travel_time_check"


def test_a_duty_on_the_own_slot_or_of_another_leader_is_ignored() -> None:
    slot_id = uuid.uuid4()
    service = PlannedService(
        uuid.uuid4(), LEADER, NORD, START, START + timedelta(minutes=90), slot_id,
    )
    own_slot = _duty(0, congregation=NORD, slot_id=slot_id)
    assert matrix_conflicts(
        [service], min_travel_minutes=30, other_bookings={LEADER: [own_slot]},
    ) == {}
    assert matrix_conflicts(
        [service], min_travel_minutes=30, other_bookings={OTHER_LEADER: [_duty(0)]},
    ) == {}


def test_a_service_during_an_absence_blocks() -> None:
    service, later = _service(0), _service(24 * 60)
    absence = (START - timedelta(hours=1), START + timedelta(hours=2))
    result = matrix_conflicts(
        [service, later], min_travel_minutes=30, unavailability={LEADER: [absence]},
    )
    assert set(result) == {service.key}
    [conflict] = result[service.key]
    assert conflict.severity == Severity.BLOCK and conflict.rule_id == "leader_available"


def test_an_absence_of_another_leader_is_ignored() -> None:
    absence = (START - timedelta(hours=1), START + timedelta(hours=2))
    assert matrix_conflicts(
        [_service(0)], min_travel_minutes=30, unavailability={OTHER_LEADER: [absence]},
    ) == {}
