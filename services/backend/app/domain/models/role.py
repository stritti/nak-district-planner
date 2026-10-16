# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/domain/models/role.py: Module."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Canonical system roles for role-based access control.

    Roles are ordered from highest to lowest privilege.
    Numeric values are used for comparison to ensure correct hierarchy.
    """

    DISTRICT_ADMIN = "DISTRICT_ADMIN"
    CONGREGATION_ADMIN = "CONGREGATION_ADMIN"
    PLANNER = "PLANNER"
    VIEWER = "VIEWER"

    def __lt__(self, other: Role) -> bool:
        """Compare roles by privilege level (higher privilege > lower privilege).

        Returns True if self has LOWER privilege than other.
        """
        # Lower index = higher privilege, so self < other means self has lower privilege
        return PRIVILEGE_ORDER.index(self) > PRIVILEGE_ORDER.index(other)

    def __le__(self, other: Role) -> bool:
        """Return True if self has at most the privilege of other."""
        return self < other or self == other

    def __gt__(self, other: Role) -> bool:
        """Return True if self has higher privilege than other."""
        return other < self

    def __ge__(self, other: Role) -> bool:
        """Return True if self has at least the privilege of other."""
        return other <= self


PRIVILEGE_ORDER: tuple[Role, ...] = (
    Role.DISTRICT_ADMIN,
    Role.CONGREGATION_ADMIN,
    Role.PLANNER,
    Role.VIEWER,
)


def roles_at_least(role: Role) -> tuple[Role, ...]:
    """Return all roles whose privilege is at least the given role.

    Single source of truth for role sets shared by Python permission guards
    and generated SQL RLS role filters.
    """
    return PRIVILEGE_ORDER[: PRIVILEGE_ORDER.index(role) + 1]


def roles_at_least_sql(role: Role) -> str:
    """Render roles_at_least as a SQL literal list for IN (...) clauses."""
    return ",".join(f"'{member.value}'" for member in roles_at_least(role))
