from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from enum import Enum


class PlanningSlotStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"


@dataclass
class PlanningSlot:
    id: uuid.UUID
    district_id: uuid.UUID
    planning_date: date
    planning_time: time
    status: PlanningSlotStatus
    created_at: datetime
    updated_at: datetime
    series_id: uuid.UUID | None = None
    congregation_id: uuid.UUID | None = None
    category: str | None = None

    @classmethod
    def create(
        cls,
        *,
        district_id: uuid.UUID,
        planning_date: date,
        planning_time: time,
        series_id: uuid.UUID | None = None,
        congregation_id: uuid.UUID | None = None,
        category: str | None = None,
        status: PlanningSlotStatus = PlanningSlotStatus.ACTIVE,
        slot_id: uuid.UUID | None = None,
    ) -> PlanningSlot:
        now = datetime.now(timezone.utc)
        return cls(
            id=slot_id or uuid.uuid4(),
            district_id=district_id,
            series_id=series_id,
            congregation_id=congregation_id,
            category=category,
            planning_date=planning_date,
            planning_time=planning_time,
            status=status,
            created_at=now,
            updated_at=now,
        )
