from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.calendar_integration import CalendarCapability, CalendarType


class CalendarIntegrationCreate(BaseModel):
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None = None
    name: str = Field(..., min_length=1, max_length=255)
    type: CalendarType
    credentials: dict  # plain dict — encrypted before storage
    sync_interval: int = Field(60, ge=1, le=10080)  # 1 min – 1 week
    capabilities: list[CalendarCapability] = Field(default_factory=lambda: [CalendarCapability.READ])


class CalendarIntegrationResponse(BaseModel):
    id: uuid.UUID
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    name: str
    type: CalendarType
    sync_interval: int
    capabilities: list[CalendarCapability]
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # credentials_enc is intentionally omitted from responses

    model_config = {"from_attributes": True}


class CalendarIntegrationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    credentials: dict | None = None  # if provided, re-encrypted before storage
    sync_interval: int | None = Field(None, ge=1, le=10080)
    capabilities: list[CalendarCapability] | None = None


class CalendarIntegrationListResponse(BaseModel):
    items: list[CalendarIntegrationResponse]
    total: int


class SyncResult(BaseModel):
    integration_id: uuid.UUID
    created: int
    updated: int
    cancelled: int
