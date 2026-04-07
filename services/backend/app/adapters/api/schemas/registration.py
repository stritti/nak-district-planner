from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.domain.models.leader import LeaderRank, SpecialRole
from app.domain.models.leader_registration import RegistrationStatus


class RegistrationCreate(BaseModel):
    """Payload submitted by the registrant (public, no auth required)."""

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    rank: LeaderRank | None = None
    congregation_id: uuid.UUID | None = None
    special_role: SpecialRole | None = None
    phone: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class RegistrationApprove(BaseModel):
    """Admin payload when approving a registration."""

    congregation_id: uuid.UUID | None = None
    rank: LeaderRank | None = None
    special_role: SpecialRole | None = None


class RegistrationReject(BaseModel):
    """Admin payload when rejecting a registration."""

    reason: str | None = Field(default=None, max_length=1000)


class RegistrationResponse(BaseModel):
    id: uuid.UUID
    district_id: uuid.UUID
    name: str
    email: str
    rank: LeaderRank | None
    congregation_id: uuid.UUID | None
    special_role: SpecialRole | None
    phone: str | None
    notes: str | None
    status: RegistrationStatus
    rejection_reason: str | None
    user_sub: str | None
    created_at: datetime
    updated_at: datetime
