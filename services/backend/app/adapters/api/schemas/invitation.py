from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.models.invitation import InvitationTargetType, OverwriteDecisionStatus


class InvitationTargetCreate(BaseModel):
    target_type: InvitationTargetType
    target_congregation_id: uuid.UUID | None = None
    external_target_note: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_target(self) -> "InvitationTargetCreate":
        if self.target_type == InvitationTargetType.DISTRICT_CONGREGATION:
            if self.target_congregation_id is None:
                raise ValueError("target_congregation_id is required for DISTRICT_CONGREGATION")
            if self.external_target_note:
                raise ValueError("external_target_note must be empty for DISTRICT_CONGREGATION")
        elif self.target_type == InvitationTargetType.EXTERNAL_NOTE:
            if not self.external_target_note:
                raise ValueError("external_target_note is required for EXTERNAL_NOTE")
            if self.target_congregation_id is not None:
                raise ValueError("target_congregation_id must be empty for EXTERNAL_NOTE")
        return self


class InvitationCreate(BaseModel):
    targets: list[InvitationTargetCreate] = Field(min_length=1)


class InvitationResponse(BaseModel):
    id: uuid.UUID
    source_event_id: uuid.UUID
    source_congregation_id: uuid.UUID
    target_type: InvitationTargetType
    target_congregation_id: uuid.UUID | None
    external_target_note: str | None
    linked_event_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class OverwriteRequestResponse(BaseModel):
    id: uuid.UUID
    invitation_id: uuid.UUID
    source_event_id: uuid.UUID
    source_event_title: str | None = None
    target_event_id: uuid.UUID
    target_event_title: str | None = None
    target_congregation_id: uuid.UUID | None = None
    current_title: str | None = None
    current_start_at: datetime | None = None
    current_end_at: datetime | None = None
    current_description: str | None = None
    current_category: str | None = None
    proposed_title: str
    proposed_start_at: datetime
    proposed_end_at: datetime
    proposed_description: str | None
    proposed_category: str | None
    status: OverwriteDecisionStatus
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OverwriteDecisionRequest(BaseModel):
    decision: OverwriteDecisionStatus

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, value: OverwriteDecisionStatus) -> OverwriteDecisionStatus:
        if value == OverwriteDecisionStatus.PENDING_OVERWRITE:
            raise ValueError("decision must be ACCEPTED or REJECTED")
        return value
