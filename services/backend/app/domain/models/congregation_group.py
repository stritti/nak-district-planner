"""app/domain/models/congregation_group.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class CongregationGroup:
    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, name: str, district_id: uuid.UUID) -> CongregationGroup:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            name=name,
            district_id=district_id,
            created_at=now,
            updated_at=now,
        )
