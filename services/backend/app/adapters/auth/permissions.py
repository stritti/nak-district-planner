"""Authorization guards and permission checks for role-based access control.

Enforces permission boundaries at the application service level based on:
- User's roles
- Scope of access (District or Congregation)
- Required role for the operation
"""

from __future__ import annotations

import uuid
from typing import Protocol

from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


class PermissionError(Exception):
    """Raised when user lacks required permissions for an operation."""

    pass


class AuthContext(Protocol):
    """Context containing user and their role assignments."""

    user_sub: str
    memberships: list[Membership]


def has_role_in_district(
    auth_context: AuthContext,
    required_role: Role,
    district_id: uuid.UUID,
    congregation_ids_in_district: set[uuid.UUID] | None = None,
) -> bool:
    """Check if user has the required role (or higher) in a district.

    Role hierarchy (highest to lowest):
    - DISTRICT_ADMIN (can do everything in the district)
    - CONGREGATION_ADMIN
    - PLANNER
    - VIEWER

    A higher role implicitly grants all permissions of lower roles.
    """
    if getattr(getattr(auth_context, "user", None), "is_superadmin", False):
        return True

    for membership in auth_context.memberships:
        if membership.scope_type == ScopeType.DISTRICT and membership.scope_id == district_id:
            # Check if user's role is sufficient
            if _role_hierarchy(membership.role) >= _role_hierarchy(required_role):
                return True

    if congregation_ids_in_district:
        for membership in auth_context.memberships:
            if (
                membership.scope_type == ScopeType.CONGREGATION
                and membership.scope_id in congregation_ids_in_district
                and _role_hierarchy(membership.role) >= _role_hierarchy(required_role)
            ):
                return True

    return False


def has_role_in_congregation(
    auth_context: AuthContext,
    required_role: Role,
    congregation_id: uuid.UUID,
) -> bool:
    """Check if user has the required role (or higher) in a congregation.

    Direct congregation membership and district-level roles are considered.
    A DISTRICT_ADMIN has all permissions in all congregations within the district.
    """
    if getattr(getattr(auth_context, "user", None), "is_superadmin", False):
        return True

    for membership in auth_context.memberships:
        # Direct congregation membership
        if (
            membership.scope_type == ScopeType.CONGREGATION
            and membership.scope_id == congregation_id
        ):
            if _role_hierarchy(membership.role) >= _role_hierarchy(required_role):
                return True
    return False


def assert_has_role_in_district(
    auth_context: AuthContext,
    required_role: Role,
    district_id: uuid.UUID,
    congregation_ids_in_district: set[uuid.UUID] | None = None,
) -> None:
    """Raise PermissionError if user lacks required role in district.
    """
    if not has_role_in_district(
        auth_context,
        required_role,
        district_id,
        congregation_ids_in_district=congregation_ids_in_district,
    ):
        raise PermissionError(
            f"User {auth_context.user_sub} lacks {required_role.value} role in district {district_id}"
        )


def assert_has_role_in_congregation(
    auth_context: AuthContext,
    required_role: Role,
    congregation_id: uuid.UUID,
) -> None:
    """Raise PermissionError if user lacks required role in congregation.
    """
    if not has_role_in_congregation(auth_context, required_role, congregation_id):
        raise PermissionError(
            f"User {auth_context.user_sub} lacks {required_role.value} role in congregation {congregation_id}"
        )


def get_districts_where_user_has_role(
    auth_context: AuthContext,
    required_role: Role,
) -> list[uuid.UUID]:
    """Get all district IDs where user has the required role (or higher).
    """
    district_ids = set()
    for membership in auth_context.memberships:
        if membership.scope_type == ScopeType.DISTRICT and _role_hierarchy(
            membership.role
        ) >= _role_hierarchy(required_role):
            district_ids.add(membership.scope_id)
    return list(district_ids)


def get_congregations_where_user_has_role(
    auth_context: AuthContext,
    required_role: Role,
) -> list[uuid.UUID]:
    """Get all congregation IDs where user has the required role (or higher).
    """
    congregation_ids = set()
    for membership in auth_context.memberships:
        if membership.scope_type == ScopeType.CONGREGATION and _role_hierarchy(
            membership.role
        ) >= _role_hierarchy(required_role):
            congregation_ids.add(membership.scope_id)
    return list(congregation_ids)


def _role_hierarchy(role: Role) -> int:
    """Return numeric rank for role hierarchy.
    Higher number = higher privilege level.
    """
    hierarchy = {
        Role.VIEWER: 1,
        Role.PLANNER: 2,
        Role.CONGREGATION_ADMIN: 3,
        Role.DISTRICT_ADMIN: 4,
    }
    return hierarchy.get(role, 0)
