"""Initialization module for seeding canonical system data.

Currently handles RBAC initialization (roles are enum-based, so no DB seeding needed).
This module can be extended to seed other canonical data as needed.
"""

from sqlalchemy.ext.asyncio import AsyncSession


async def seed_canonical_roles(session: AsyncSession) -> None:
    """Ensure canonical RBAC roles are available in the system.

    Canonical roles are:
    - DISTRICT_ADMIN: Full control over a district
    - CONGREGATION_ADMIN: Full control over a congregation
    - PLANNER: Can plan and modify planning slots
    - VIEWER: Read-only access

    Note: Roles themselves are defined in the Role enum and don't require DB seeding.
    Memberships (user + role + scope assignments) are created on-demand via repositories.
    """
    # Roles are enum-based; no database seeding required
    # This function is provided for completeness and future extensibility
    pass
