from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.domain.planning.conflict_rules import no_double_booking
from app.domain.planning.conflict_result import ConflictContext, ExistingAssignment, Severity


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