"""District-owned monthly reminder configuration and date rules."""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time

from app.domain.models.role import Role


@dataclass
class DistrictReminderConfig:
    id: uuid.UUID
    district_id: uuid.UUID
    day_of_month: int
    time_of_day: time
    subject_template: str
    body_template: str
    recipient_role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Validate scheduling fields."""
        if not 1 <= self.day_of_month <= 31:
            raise ValueError("day_of_month must be between 1 and 31")
        if self.time_of_day.tzinfo is not None:
            raise ValueError("time_of_day must be a local, timezone-naive time")
        if not self.subject_template.strip() or not self.body_template.strip():
            raise ValueError("subject_template and body_template cannot be blank")
        if not isinstance(self.recipient_role, Role):
            self.recipient_role = Role(self.recipient_role)

    @classmethod
    def create(
        cls,
        *,
        district_id: uuid.UUID,
        day_of_month: int,
        time_of_day: time,
        subject_template: str,
        body_template: str,
        recipient_role: Role,
        is_active: bool = True,
    ) -> DistrictReminderConfig:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            district_id=district_id,
            day_of_month=day_of_month,
            time_of_day=time_of_day,
            subject_template=subject_template,
            body_template=body_template,
            recipient_role=recipient_role,
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )

    def is_due(self, local_now: datetime) -> bool:
        """Assess one configured monthly occurrence in the scheduler's local timezone."""
        last_day = calendar.monthrange(local_now.year, local_now.month)[1]
        scheduled_day = min(self.day_of_month, last_day)
        return (
            self.is_active
            and local_now.date() == date(local_now.year, local_now.month, scheduled_day)
            and local_now.time().replace(tzinfo=None) >= self.time_of_day
        )
