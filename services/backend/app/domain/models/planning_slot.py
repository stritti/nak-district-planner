from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from enum import Enum

from app.domain.models.event import EventApprovalStatus


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
    # Title for the slot (used when no EventInstance exists or as fallback)
    title: str | None = None
    # Approval status for planning workflow (migrated from Event.approval_status)
    approval_status: EventApprovalStatus | None = None
    # Invitation tracking fields (migrated from Event)
    invitation_source_congregation_id: uuid.UUID | None = None
    invitation_source_event_id: uuid.UUID | None = None
    # List of congregation IDs that this slot applies to (for district-wide holidays)
    applicability: list[uuid.UUID] = field(default_factory=list)

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
        title: str | None = None,
        approval_status: EventApprovalStatus | None = None,
        invitation_source_congregation_id: uuid.UUID | None = None,
        invitation_source_event_id: uuid.UUID | None = None,
        applicability: list[uuid.UUID] | None = None,
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
            title=title,
            approval_status=approval_status,
            invitation_source_congregation_id=invitation_source_congregation_id,
            invitation_source_event_id=invitation_source_event_id,
            applicability=applicability or [],
            planning_date=planning_date,
            planning_time=planning_time,
            status=status,
            created_at=now,
            updated_at=now,
        )
