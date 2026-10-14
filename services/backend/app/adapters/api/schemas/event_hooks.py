# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""HTTP representations of event mail hooks."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.events import EventType
from app.domain.models.role import Role


class EventHookCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    recipient_role: Role
    subject_template: str = Field(min_length=1, max_length=500)
    body_template: str = Field(min_length=1, max_length=20000)
    is_active: bool = True


class EventHookUpdate(BaseModel):
    """Full replacement of the mutable fields (PUT); the event type is immutable."""

    model_config = ConfigDict(extra="forbid")

    recipient_role: Role
    subject_template: str = Field(min_length=1, max_length=500)
    body_template: str = Field(min_length=1, max_length=20000)
    is_active: bool


class EventHookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    district_id: uuid.UUID
    event_type: EventType
    recipient_role: Role
    subject_template: str
    body_template: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EventTypeInfo(BaseModel):
    event_type: EventType
    placeholders: list[str]
