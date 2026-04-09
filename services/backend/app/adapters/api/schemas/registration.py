from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.domain.models.leader import LeaderRank, SpecialRole
from app.domain.models.leader_registration import RegistrationStatus
from app.domain.models.membership import ScopeType
from app.domain.models.role import Role


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

    role: Role
    scope_type: ScopeType
    scope_id: uuid.UUID
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
    assigned_role: Role | None
    assigned_scope_type: ScopeType | None
    assigned_scope_id: uuid.UUID | None
    approved_by_sub: str | None
    approved_at: datetime | None
    idp_provision_status: str | None
    idp_provision_error: str | None
    idp_provisioned_at: datetime | None
    created_at: datetime
    updated_at: datetime
