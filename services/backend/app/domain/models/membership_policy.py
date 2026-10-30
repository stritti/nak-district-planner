# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Who may manage which membership, and which roles a unit can carry.

Pure rules for user administration. A unit is a district or a congregation;
the caller resolves a congregation's district before asking.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from .membership import Membership, ScopeType
from .role import Role

# DISTRICT_ADMIN only exists on districts, CONGREGATION_ADMIN only on congregations.
ROLES_BY_SCOPE: dict[ScopeType, frozenset[Role]] = {
    ScopeType.DISTRICT: frozenset({Role.DISTRICT_ADMIN, Role.PLANNER, Role.VIEWER}),
    ScopeType.CONGREGATION: frozenset({Role.CONGREGATION_ADMIN, Role.PLANNER, Role.VIEWER}),
}

# The lowest role that may manage the memberships of a unit of that type.
_ADMIN_ROLE: dict[ScopeType, Role] = {
    ScopeType.DISTRICT: Role.DISTRICT_ADMIN,
    ScopeType.CONGREGATION: Role.CONGREGATION_ADMIN,
}


def role_fits_scope(role: Role, scope_type: ScopeType) -> bool:
    return role in ROLES_BY_SCOPE[scope_type]


def management_level(
    memberships: Iterable[Membership],
    *,
    is_superadmin: bool,
    scope_type: ScopeType,
    scope_id: uuid.UUID,
    district_id: uuid.UUID,
) -> Role | None:
    """The highest role the actor may grant or remove in the unit, or None.

    ``district_id`` is the unit itself for a district and the parent district
    for a congregation. A district admin manages the district and all its
    congregations; a congregation admin manages only that congregation and
    can never touch district memberships.
    """
    if is_superadmin:
        return Role.DISTRICT_ADMIN
    roles = [
        m.role
        for m in memberships
        if (m.scope_type == ScopeType.DISTRICT and m.scope_id == district_id)
        or (
            scope_type == ScopeType.CONGREGATION
            and m.scope_type == ScopeType.CONGREGATION
            and m.scope_id == scope_id
        )
    ]
    if not roles:
        return None
    level = max(roles)
    return level if level >= _ADMIN_ROLE[scope_type] else None


def may_manage(level: Role | None, *roles: Role | None) -> bool:
    """True if every given role (new and existing) is at most the actor's level."""
    return level is not None and all(role is None or role <= level for role in roles)


def manages_any_unit(memberships: Iterable[Membership], *, is_superadmin: bool) -> bool:
    """Whether the actor may open user administration at all."""
    if is_superadmin:
        return True
    # A congregation admin role on a district (legacy data) manages its congregations.
    return any(m.role >= Role.CONGREGATION_ADMIN for m in memberships)
