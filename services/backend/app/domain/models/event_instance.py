from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.models.event import EventSource, EventVisibility


@dataclass
class EventInstance:
    id: uuid.UUID
    planning_slot_id: uuid.UUID
    title: str
    actual_start_at: datetime
    actual_end_at: datetime
    source: EventSource
    visibility: EventVisibility
    deviation_flag: bool
    created_at: datetime
    updated_at: datetime
    description: str | None = None

    @classmethod
    def create(
        cls,
        *,
        planning_slot_id: uuid.UUID,
        title: str,
        actual_start_at: datetime,
        actual_end_at: datetime,
        source: EventSource,
        visibility: EventVisibility,
        description: str | None = None,
        deviation_flag: bool = False,
        instance_id: uuid.UUID | None = None,
    ) -> EventInstance:
        now = datetime.now(timezone.utc)
        return cls(
            id=instance_id or uuid.uuid4(),
            planning_slot_id=planning_slot_id,
            title=title,
            description=description,
            actual_start_at=actual_start_at,
            actual_end_at=actual_end_at,
            source=source,
            visibility=visibility,
            deviation_flag=deviation_flag,
            created_at=now,
            updated_at=now,
        )
