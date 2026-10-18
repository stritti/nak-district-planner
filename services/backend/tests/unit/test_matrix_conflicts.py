# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Conflicts shown in the matrix: double booking and short travel time per leader (step 3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.domain.planning.conflict_result import Severity
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
