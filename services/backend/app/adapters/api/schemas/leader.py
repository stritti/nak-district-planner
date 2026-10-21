# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/api/schemas/leader.py: Module."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models.leader import ROLE_LEVEL_MESSAGE, LeaderRank, SpecialRole, role_fits_level


class LeaderAssignmentCreate(BaseModel):
    """One service of a leader: a congregation (``None`` = district level) with an optional role."""

    model_config = ConfigDict(extra="forbid")
    congregation_id: uuid.UUID | None = None
    role: SpecialRole | None = None
    is_home: bool = False

    @model_validator(mode="after")
    def _role_fits_the_level(self) -> LeaderAssignmentCreate:
        if not role_fits_level(self.role, self.congregation_id):
            raise ValueError(ROLE_LEVEL_MESSAGE)
        return self


class LeaderAssignmentUpdate(BaseModel):
    """Change the role or make this assignment the home assignment (``true`` only)."""

    model_config = ConfigDict(extra="forbid")
    role: SpecialRole | None = None
    is_home: bool | None = None


class LeaderAssignmentResponse(BaseModel):
    id: uuid.UUID
    congregation_id: uuid.UUID | None
    role: SpecialRole | None
    is_home: bool
    revision: str


def check_assignments(items: list[LeaderAssignmentCreate]) -> None:
    """A lone assignment is the home; otherwise exactly one home and each congregation once."""
    if len(items) == 1:
        items[0].is_home = True
    if sum(item.is_home for item in items) != 1:
        raise ValueError("Genau eine Zuordnung muss die Heimat-Zuordnung sein.")
    if len({item.congregation_id for item in items}) != len(items):
        raise ValueError("Jede Gemeinde darf nur einmal zugeordnet werden.")


class LeaderCreate(BaseModel):
    """LeaderCreate."""

    name: str = Field(min_length=1, max_length=255)
    rank: LeaderRank | None = None
    # Omitted: one district-level home assignment without a role.
    assignments: list[LeaderAssignmentCreate] | None = Field(default=None, min_length=1)
    user_sub: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool = True
    hidden_from_lists: bool = False
    service_end_date: date | None = None
    # Set after the user confirmed that a same-named person is a different one.
    confirm_duplicate: bool = False

    @model_validator(mode="after")
    def _one_home_and_no_repeats(self) -> LeaderCreate:
        if self.assignments is not None:
            check_assignments(self.assignments)
        return self


class LeaderUpdate(BaseModel):
    """LeaderUpdate."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    rank: LeaderRank | None = None
    user_sub: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool | None = None
    hidden_from_lists: bool | None = None
    service_end_date: date | None = None


class LeaderResponse(BaseModel):
    """LeaderResponse."""

    id: uuid.UUID
    name: str
    district_id: uuid.UUID
    rank: LeaderRank | None
    assignments: list[LeaderAssignmentResponse]
    user_sub: str | None
    email: str | None
    phone: str | None
    notes: str | None
    is_active: bool
    hidden_from_lists: bool = False
    service_end_date: date | None = None
    created_at: datetime
    updated_at: datetime
    revision: str


class LeaderSelfLinkRequest(BaseModel):
    """LeaderSelfLinkRequest."""

    leader_id: uuid.UUID


class LeaderSelfLinkResponse(BaseModel):
    """LeaderSelfLinkResponse."""

    linked: bool
    leader: LeaderResponse | None = None
