from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.models.leader_unavailability import (
    LeaderUnavailability,
    UnavailabilityReason,
)


def test_leader_unavailability_create_sets_identity_and_timestamps() -> None:
    leader_id = uuid.uuid4()
    start_at = datetime(2026, 2, 1, 0, 0, tzinfo=UTC)
    end_at = start_at + timedelta(days=2)

    absence = LeaderUnavailability.create(
        leader_id=leader_id,
        start_at=start_at,
        end_at=end_at,
        reason=UnavailabilityReason.VACATION,
        note="Familienurlaub",
    )

    assert absence.id
    assert absence.leader_id == leader_id
    assert absence.start_at == start_at
    assert absence.end_at == end_at
    assert absence.reason is UnavailabilityReason.VACATION
    assert absence.note == "Familienurlaub"
    assert absence.created_at.tzinfo is not None
    assert absence.updated_at == absence.created_at


def test_leader_unavailability_rejects_empty_or_reversed_period() -> None:
    start_at = datetime(2026, 2, 1, 0, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="end_at muss nach start_at liegen"):
        LeaderUnavailability.create(
            leader_id=uuid.uuid4(),
            start_at=start_at,
            end_at=start_at,
            reason=UnavailabilityReason.BLOCKED,
        )
