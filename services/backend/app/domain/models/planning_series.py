from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from typing import Any


@dataclass
class PlanningSeries:
    id: uuid.UUID
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    category: str | None
    default_planning_time: time
    recurrence_pattern: dict[str, Any] = field(default_factory=dict)
    active_from: date | None = None
    active_until: date | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        *,
        district_id: uuid.UUID,
        default_planning_time: time,
        congregation_id: uuid.UUID | None = None,
        category: str | None = None,
        recurrence_pattern: dict[str, Any] | None = None,
        active_from: date | None = None,
        active_until: date | None = None,
        is_active: bool = True,
    ) -> PlanningSeries:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            district_id=district_id,
            congregation_id=congregation_id,
            category=category,
            default_planning_time=default_planning_time,
            recurrence_pattern=recurrence_pattern or {},
            active_from=active_from,
            active_until=active_until,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
