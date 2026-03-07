from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class AssignmentStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    CONFIRMED = "CONFIRMED"


@dataclass
class ServiceAssignment:
    id: uuid.UUID
    event_id: uuid.UUID
    leader_name: str
    status: AssignmentStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        event_id: uuid.UUID,
        leader_name: str,
        status: AssignmentStatus = AssignmentStatus.OPEN,
    ) -> ServiceAssignment:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            event_id=event_id,
            leader_name=leader_name,
            status=status,
            created_at=now,
            updated_at=now,
        )
