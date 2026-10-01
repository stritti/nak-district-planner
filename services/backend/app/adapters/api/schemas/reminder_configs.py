"""HTTP representations of monthly reminder configurations."""

from __future__ import annotations

import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models.role import Role


class ReminderConfigCreate(BaseModel):
    day_of_month: int = Field(ge=1, le=31)
    time_of_day: time
    subject_template: str = Field(min_length=1, max_length=500)
    body_template: str = Field(min_length=1, max_length=20000)
    recipient_role: Role
    is_active: bool = True


class ReminderConfigUpdate(BaseModel):
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    time_of_day: time | None = None
    subject_template: str | None = Field(default=None, min_length=1, max_length=500)
    body_template: str | None = Field(default=None, min_length=1, max_length=20000)
    recipient_role: Role | None = None
    is_active: bool | None = None


class ReminderConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
