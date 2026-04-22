"""app/domain/models/membership.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, StrEnum

from .role import Role


class ScopeType(StrEnum):
    """Scope type for membership assignments."""

    DISTRICT = "DISTRICT"
    CONGREGATION = "CONGREGATION"


@dataclass
class Membership:
    """Represents a role assignment for a user within a specific scope.

    A user can have multiple memberships across different districts and congregations,
    each with a potentially different role.

    Attributes:
        id: Unique identifier for the membership
        user_sub: OIDC subject identifier (foreign key to User)
        role: The role assigned (DISTRICT_ADMIN, CONGREGATION_ADMIN, PLANNER, VIEWER)
        scope_type: Whether the scope is a DISTRICT or CONGREGATION
        scope_id: ID of the district or congregation
        created_at: When the membership was created
        updated_at: When the membership was last updated
    """

    id: uuid.UUID
    user_sub: str
    role: Role
    scope_type: ScopeType
    scope_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_sub: str,
        role: Role,
        scope_type: ScopeType,
        scope_id: uuid.UUID,
    ) -> Membership:
        """Create a new membership."""
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            user_sub=user_sub,
            role=role,
            scope_type=scope_type,
            scope_id=scope_id,
            created_at=now,
            updated_at=now,
        )
