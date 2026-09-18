"""Pydantic schemas for leader unavailability periods."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.domain.models.leader_unavailability import UnavailabilityReason


class LeaderUnavailabilityCreate(BaseModel):
    leader_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    reason: UnavailabilityReason
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_period(self) -> LeaderUnavailabilityCreate:
        if self.end_at <= self.start_at:
            raise ValueError("end_at muss nach start_at liegen")
        return self


class LeaderUnavailabilityUpdate(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    reason: UnavailabilityReason | None = None
    note: str | None = Field(default=None, max_length=2000)


class LeaderUnavailabilityResponse(BaseModel):
    id: uuid.UUID
    leader_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    reason: UnavailabilityReason
    note: str | None
    created_at: datetime
    updated_at: datetime
