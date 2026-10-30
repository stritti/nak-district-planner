# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Schemas of the user administration (memberships per unit, superadmin status)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field, model_validator

from app.domain.models.membership import ScopeType
from app.domain.models.membership_policy import role_fits_scope
from app.domain.models.role import Role


class AdminMembershipOut(BaseModel):
    """One membership as shown in user administration."""

    id: uuid.UUID
    role: Role
    scope_type: ScopeType
    scope_id: uuid.UUID
    scope_name: str | None = Field(default=None, description="Name of the district or congregation")
    district_id: uuid.UUID = Field(
        description="The district itself, or the congregation's district"
    )


class AdminUserOut(BaseModel):
    """A registered user with the memberships the caller may manage."""

    sub: str
    email: str
    username: str
    name: str | None = None
    is_superadmin: bool | None = Field(
        default=None, description="Only reported to superadmins; null for other administrators"
    )
    memberships: list[AdminMembershipOut] = Field(default_factory=list)


class MembershipAssign(BaseModel):
    """Assign a role in one unit; an existing membership of that unit is updated."""

    scope_type: ScopeType
    scope_id: uuid.UUID
    role: Role

    @model_validator(mode="after")
    def _role_fits_scope(self) -> MembershipAssign:
        if not role_fits_scope(self.role, self.scope_type):
            raise ValueError(
                f"Rolle {self.role.value} ist für {self.scope_type.value} nicht vorgesehen."
            )
        return self


class SuperadminUpdate(BaseModel):
    """Grant or revoke the global superadmin status."""

    is_superadmin: bool
