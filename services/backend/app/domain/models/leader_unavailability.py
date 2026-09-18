from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class UnavailabilityReason(StrEnum):
    """Reason for a leader being unavailable for assignments."""

    VACATION = "URLAUB"
    BLOCKED = "SPERRZEIT"
    TRAINING = "FORTBILDUNG"
    OTHER = "SONSTIGES"


@dataclass
class LeaderUnavailability:
    """A manually maintained unavailability period for a leader."""

    id: uuid.UUID
    leader_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    reason: UnavailabilityReason
    note: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        leader_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
        reason: UnavailabilityReason,
        note: str | None = None,
    ) -> LeaderUnavailability:
        if end_at <= start_at:
            raise ValueError("end_at muss nach start_at liegen")
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            leader_id=leader_id,
            start_at=start_at,
            end_at=end_at,
            reason=reason,
            note=note,
            created_at=now,
            updated_at=now,
        )
