# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""API schemas for the /api/v1/events endpoints.

Extracted from the router module so request/response contracts live with the
other adapter schemas while the router keeps only handler logic.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.adapters.api.schemas.conflict import ConflictItem
from app.domain.models.event_instance import (
    EventSource,
    EventVisibility,
    SyncState,
)
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlotStatus
from app.domain.models.service_assignment import AssignmentStatus


class EventResponsible(BaseModel):
    """Person in charge of an event; for a Gottesdienst this is the Dienstleiter."""

    assignment_id: uuid.UUID
    needs_review: bool = False
    leader_id: uuid.UUID | None
    name: str
    status: AssignmentStatus


class EventResponse(BaseModel):
    """Event as seen by the frontend: PlanningSlot + optional EventInstance."""

    id: uuid.UUID
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    district_id: uuid.UUID
    congregation_id: uuid.UUID | None
    category: str | None
    is_service: bool
    planning_date: date | None = None
    source: EventSource
    status: PlanningSlotStatus
    approval_status: EventApprovalStatus | None
    was_released: bool
    visibility: EventVisibility
    applicability: list[str]
    invitation_source_congregation_id: uuid.UUID | None = None
    invitation_source_event_id: uuid.UUID | None = None
    sync_state: SyncState | None = None
    responsible: EventResponsible | None = None
    created_at: datetime
    updated_at: datetime
    revision: str


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    limit: int
    offset: int


class EventCreate(BaseModel):
    """Create a manual, initially unpublished planning slot and occurrence."""

    model_config = ConfigDict(extra="forbid")

    district_id: uuid.UUID
    congregation_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category: str | None = Field(default=None, max_length=255)
    start_at: datetime
    end_at: datetime
    visibility: EventVisibility = EventVisibility.PUBLIC
    applicability: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(
        default_factory=list, max_length=500
    )


class EventInlineUpdate(BaseModel):
    """Explicit scalar-only contract; reject future workflow fields by default."""

    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None


class DutyImpactAcknowledgement(BaseModel):
    """What the client saw in the change-impact preview and explicitly accepted."""

    model_config = ConfigDict(extra="forbid")

    newly_flagged: int = Field(0, ge=0)
    newly_quarantined: int = Field(0, ge=0)


class EventUpdate(BaseModel):
    """Strict full-editor request, including explicit workflow acknowledgement."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    congregation_id: uuid.UUID | None = None
    status: PlanningSlotStatus | None = None
    approval_status: EventApprovalStatus | None = None
    category: str | None = Field(None, max_length=255)
    applicability: list[Annotated[str, Field(min_length=1, max_length=64)]] | None = Field(
        None, max_length=500
    )
    confirm_warnings: bool = Field(
        False,
        description="Acknowledge WARN conflicts on dependent changes; not an event data field.",
    )
    acknowledged_duty_impact: DutyImpactAcknowledgement | None = Field(
        None,
        description=(
            "Duty reviews/quarantines the client accepted. The server recomputes the impact "
            "under the slot lock and rejects the write (409) if more would be affected."
        ),
    )


class EventChangeImpactRequest(BaseModel):
    """Schedule fields for a dry-run impact check; nothing is persisted."""

    model_config = ConfigDict(extra="forbid")

    start_at: datetime | None = None
    end_at: datetime | None = None
    congregation_id: uuid.UUID | None = None
    category: str | None = Field(default=None, max_length=255)


class EventChangeImpactItem(BaseModel):
    assignment_id: uuid.UUID
    leader_id: uuid.UUID
    conflicts: list[ConflictItem]


class EventChangeImpact(BaseModel):
    blocked: bool
    requires_confirmation: bool
    items: list[EventChangeImpactItem]
    duties_newly_flagged: int = Field(
        0, description="Duty assignments that would newly need review (category/congregation change)."
    )
    duties_newly_quarantined: int = Field(
        0, description="Duty assignments that would newly be hidden from the new scope."
    )
    duties_flagged_after: int = 0
    duties_quarantined_after: int = Field(
        0, description="Duty assignments hidden from the new scope until revalidated."
    )


class BulkApprovalStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    year: int = Field(ge=1900, le=9999)
    month: int = Field(ge=1, le=12)
    approval_status: EventApprovalStatus
    congregation_id: uuid.UUID | None = None


class BulkApprovalStatusResponse(BaseModel):
    updated_count: int


