from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.leader import LeaderRank, SpecialRole


class LeaderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    rank: LeaderRank | None = None
    congregation_id: uuid.UUID | None = None
    special_role: SpecialRole | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool = True


class LeaderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    rank: LeaderRank | None = None
    congregation_id: uuid.UUID | None = None
    special_role: SpecialRole | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class LeaderResponse(BaseModel):
    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    rank: LeaderRank | None
    congregation_id: uuid.UUID | None
    special_role: SpecialRole | None
    email: str | None
    phone: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
