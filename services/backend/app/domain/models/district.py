from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class District:
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, name: str) -> District:
        now = datetime.now(timezone.utc)
        return cls(id=uuid.uuid4(), name=name, created_at=now, updated_at=now)
