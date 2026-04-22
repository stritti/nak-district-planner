"""app/domain/models/service_assignment.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class AssignmentStatus(str, Enum):
    """AssignmentStatus domain model."""

    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    CONFIRMED = "CONFIRMED"


@dataclass
class ServiceAssignment:
    id: uuid.UUID
    event_id: uuid.UUID
    leader_id: uuid.UUID | None
    leader_name: str | None
    status: AssignmentStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        event_id: uuid.UUID,
        leader_id: uuid.UUID | None = None,
        leader_name: str | None = None,
        status: AssignmentStatus = AssignmentStatus.OPEN,
    ) -> ServiceAssignment:
        if leader_id is None and not leader_name:
            raise ValueError("Entweder leader_id oder leader_name muss gesetzt sein")
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            event_id=event_id,
            leader_id=leader_id,
            leader_name=leader_name,
            status=status,
            created_at=now,
            updated_at=now,
        )
