# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Scope-aware recurring-event access policy.

Keep membership decisions outside HTTP route bodies and require parent-district
validation before accepting congregation-scoped access.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.deps import CurrentUserWithMemberships
from app.adapters.auth.permissions import has_role_in_district, require_role_in_district
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.domain.models.membership import ScopeType
from app.domain.models.recurring_event_template import RecurringEventTemplate
from app.domain.models.role import Role


def _is_congregation_admin(auth: CurrentUserWithMemberships, congregation_id: uuid.UUID) -> bool:
    return any(
        membership.scope_type is ScopeType.CONGREGATION
        and membership.scope_id == congregation_id
        and membership.role is Role.CONGREGATION_ADMIN
        for membership in auth.memberships
    )


def _require_write(
    auth: CurrentUserWithMemberships,
    district_id: uuid.UUID,
    congregation_id: uuid.UUID | None,
) -> None:
    if has_role_in_district(auth, Role.DISTRICT_ADMIN, district_id):
        return
    if congregation_id is not None and _is_congregation_admin(auth, congregation_id):
        return
    require_role_in_district(auth, Role.DISTRICT_ADMIN, district_id)


def _visible(auth: CurrentUserWithMemberships, entry: RecurringEventTemplate) -> bool:
    if has_role_in_district(auth, Role.VIEWER, entry.district_id):
        return True
    return any(
        membership.scope_type is ScopeType.CONGREGATION
        and (
            membership.scope_id == entry.congregation_id
            or (
                entry.congregation_id is None
                and (
                    "all" in entry.applicability
                    or str(membership.scope_id) in entry.applicability
                )
            )
        )
        for membership in auth.memberships
    )


async def _require_read(
    auth: CurrentUserWithMemberships,
    district_id: uuid.UUID,
    session: AsyncSession,
) -> set[uuid.UUID] | None:
    """Return None for district-wide readers, or authorized congregations."""
    if has_role_in_district(auth, Role.VIEWER, district_id):
        return None
    congregations = await SqlCongregationRepository(session).list_by_district(district_id)
    district_congregations = {congregation.id for congregation in congregations}
    authorized = {
        membership.scope_id
        for membership in auth.memberships
        if membership.scope_type is ScopeType.CONGREGATION
        and membership.scope_id in district_congregations
    }
    if authorized:
        return authorized
    require_role_in_district(auth, Role.VIEWER, district_id)
    return set()
