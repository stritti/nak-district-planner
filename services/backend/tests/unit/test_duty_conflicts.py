# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""One person cannot hold duties at overlapping times (step 2.2a)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.domain.planning.conflict_result import Severity
from app.domain.planning.duty_conflicts import ScheduledDuty, duty_identity_conflicts

START = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
END = START + timedelta(minutes=90)
HERE, ELSEWHERE = uuid.uuid4(), uuid.uuid4()


def _other(offset_minutes: int = 0, *, strong: bool = True, congregation=ELSEWHERE) -> ScheduledDuty:
    start = START + timedelta(minutes=offset_minutes)
    return ScheduledDuty(
        slot_id=uuid.uuid4(), congregation_id=congregation, start_time=start,
        end_time=start + timedelta(minutes=90), strong=strong,
    )


def test_no_other_duty_means_no_conflict() -> None:
    assert duty_identity_conflicts(START, END, []) == []


def test_overlapping_duty_of_a_verified_identity_blocks() -> None:
    [conflict] = duty_identity_conflicts(START, END, [_other(30)])
    assert conflict.severity == Severity.BLOCK
    assert conflict.rule_id == "duty_double_booking"
    assert conflict.details["existing_congregation_id"] == ELSEWHERE


def test_overlapping_duty_found_only_by_name_warns() -> None:
    [conflict] = duty_identity_conflicts(START, END, [_other(0, strong=False)])
    assert conflict.severity == Severity.WARN
    assert conflict.rule_id == "duty_possible_namesake"


def test_a_duty_in_the_same_congregation_at_the_same_time_also_conflicts() -> None:
    [conflict] = duty_identity_conflicts(START, END, [_other(10, congregation=HERE)])
    assert conflict.severity == Severity.BLOCK


def test_back_to_back_duties_do_not_overlap() -> None:
    assert duty_identity_conflicts(START, END, [_other(90), _other(-90)]) == []


def test_one_result_per_severity_with_a_strong_match_taking_precedence() -> None:
    results = duty_identity_conflicts(
        START, END, [_other(0, strong=False), _other(30), _other(60, strong=False)]
    )
    assert [r.severity for r in results] == [Severity.BLOCK, Severity.WARN]
