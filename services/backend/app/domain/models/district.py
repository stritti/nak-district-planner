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
    state_code: str | None = None  # 2-letter German state code, e.g. "BY"

    @classmethod
    def create(cls, *, name: str, state_code: str | None = None) -> District:
        now = datetime.now(timezone.utc)
        return cls(id=uuid.uuid4(), name=name, created_at=now, updated_at=now, state_code=state_code)
