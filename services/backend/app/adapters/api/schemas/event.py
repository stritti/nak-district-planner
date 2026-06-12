"""app/adapters/api/schemas/event.py: Module."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.event import EventApprovalStatus, EventSource, EventStatus, EventVisibility


class EventCreate(BaseModel):
    """EventCreate."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    start_at: datetime
    end_at: datetime
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None = None
    category: str | None = None
    source: EventSource = EventSource.INTERNAL
    status: EventStatus = EventStatus.DRAFT
    approval_status: EventApprovalStatus = EventApprovalStatus.PLANNED
    visibility: EventVisibility = EventVisibility.INTERNAL
    audiences: list[str] = Field(default_factory=list)
    applicability: list[uuid.UUID] = Field(default_factory=list)


class EventResponse(BaseModel):
    """EventResponse."""

    id: uuid.UUID
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    category: str | None
    source: EventSource
    status: EventStatus
    approval_status: EventApprovalStatus
    visibility: EventVisibility
    audiences: list[str]
    applicability: list[uuid.UUID]
    invitation_source_congregation_id: uuid.UUID | None = None
    invitation_source_congregation_name: str | None = None
    invitation_source_event_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventUpdate(BaseModel):
    """Partial update — only fields present in the request body are changed."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    district_id: uuid.UUID | None = None
    congregation_id: uuid.UUID | None = None
    status: EventStatus | None = None
    approval_status: EventApprovalStatus | None = None
    category: str | None = None


class BulkApprovalStatusRequest(BaseModel):
    """BulkApprovalStatusRequest."""

    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)
    approval_status: EventApprovalStatus
    congregation_id: uuid.UUID | None = None


class BulkApprovalStatusResponse(BaseModel):
    """BulkApprovalStatusResponse."""

    updated_count: int


class EventListResponse(BaseModel):
    """EventListResponse."""

    items: list[EventResponse]
    total: int
    limit: int
    offset: int
