from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.domain.planning.conflict_result import (
    ConflictContext,
    ConflictResult,
    ExistingAssignment,
    Severity,
)
from app.domain.planning.conflict_rules import (
    leader_available,
    no_double_booking,
    role_requirement_check,
    travel_time_check,
)
from app.domain.planning.conflict_service import ConflictService


def test_no_double_booking_blocks_overlapping_assignment() -> None:
    leader_id = uuid.uuid4()
    start_time = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)
    context = ConflictContext(
        leader_id=leader_id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        congregation_id=uuid.uuid4(),
        existing_assignments=(
            ExistingAssignment(
                leader_id=leader_id,
                start_time=start_time + timedelta(minutes=30),
                end_time=start_time + timedelta(hours=1, minutes=30),
                congregation_id=uuid.uuid4(),
            ),
        ),
    )

    result = no_double_booking(context)

    assert result is not None
    assert result.rule_id == "no_double_booking"
    assert result.severity is Severity.BLOCK


def test_no_double_booking_allows_adjacent_assignment() -> None:
    leader_id = uuid.uuid4()
    start_time = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)
    context = ConflictContext(
        leader_id=leader_id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        congregation_id=uuid.uuid4(),
        existing_assignments=(
            ExistingAssignment(
                leader_id=leader_id,
                start_time=start_time - timedelta(hours=1),
                end_time=start_time,
                congregation_id=uuid.uuid4(),
            ),
        ),
    )

    assert no_double_booking(context) is None


def test_conflict_service_collects_results_from_rules() -> None:
    context = ConflictContext(
        leader_id=uuid.uuid4(),
        start_time=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 1, 11, 10, 0, tzinfo=UTC),
        congregation_id=uuid.uuid4(),
    )
    expected = ConflictResult(
        rule_id="test_rule",
        severity=Severity.WARN,
        message="Hinweis",
    )

    service = ConflictService(rules=(lambda _: expected,))

    assert service.check(context) == [expected]


def test_travel_time_check_warns_when_congregations_are_too_close() -> None:
    leader_id = uuid.uuid4()
    first_congregation_id = uuid.uuid4()
    second_congregation_id = uuid.uuid4()
    start_time = datetime(2026, 1, 11, 9, 30, tzinfo=UTC)
    context = ConflictContext(
        leader_id=leader_id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        congregation_id=second_congregation_id,
        existing_assignments=(
            ExistingAssignment(
                leader_id=leader_id,
                start_time=start_time - timedelta(hours=1),
                end_time=start_time - timedelta(minutes=15),
                congregation_id=first_congregation_id,
            ),
        ),
        min_travel_minutes=30,
    )

    result = travel_time_check(context)

    assert result is not None
    assert result.rule_id == "travel_time_check"
    assert result.severity is Severity.WARN


def test_travel_time_check_allows_sufficient_gap() -> None:
    leader_id = uuid.uuid4()
    start_time = datetime(2026, 1, 11, 10, 0, tzinfo=UTC)
    context = ConflictContext(
        leader_id=leader_id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        congregation_id=uuid.uuid4(),
        existing_assignments=(
            ExistingAssignment(
                leader_id=leader_id,
                start_time=start_time - timedelta(hours=2),
                end_time=start_time - timedelta(minutes=30),
                congregation_id=uuid.uuid4(),
            ),
        ),
        min_travel_minutes=30,
    )

    assert travel_time_check(context) is None


def test_role_requirement_check_blocks_insufficient_rank() -> None:
    context = ConflictContext(
        leader_id=uuid.uuid4(),
        start_time=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 1, 11, 10, 0, tzinfo=UTC),
        congregation_id=uuid.uuid4(),
        leader_rank="Di.",
        required_role="Pr.",
    )

    result = role_requirement_check(context)

    assert result is not None
    assert result.rule_id == "role_requirement_check"
    assert result.severity is Severity.BLOCK


def test_role_requirement_check_allows_higher_rank() -> None:
    context = ConflictContext(
        leader_id=uuid.uuid4(),
        start_time=datetime(2026, 1, 11, 9, 0, tzinfo=UTC),
        end_time=datetime(2026, 1, 11, 10, 0, tzinfo=UTC),
        congregation_id=uuid.uuid4(),
        leader_rank="Ev.",
        required_role="Pr.",
    )

    assert role_requirement_check(context) is None


def test_leader_available_blocks_unavailability_overlap() -> None:
    start_time = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)
    context = ConflictContext(
        leader_id=uuid.uuid4(),
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        congregation_id=uuid.uuid4(),
        unavailability_periods=(
            (start_time + timedelta(minutes=30), start_time + timedelta(hours=2)),
        ),
    )

    result = leader_available(context)

    assert result is not None
    assert result.rule_id == "leader_available"
    assert result.severity is Severity.BLOCK


def test_leader_available_allows_assignment_outside_unavailability() -> None:
    start_time = datetime(2026, 1, 11, 9, 0, tzinfo=UTC)
    context = ConflictContext(
        leader_id=uuid.uuid4(),
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        congregation_id=uuid.uuid4(),
        unavailability_periods=(
            (start_time + timedelta(hours=1), start_time + timedelta(hours=2)),
        ),
    )

    assert leader_available(context) is None
