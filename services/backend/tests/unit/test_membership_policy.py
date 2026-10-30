# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Who may manage which membership (user administration rules)."""

from __future__ import annotations

import uuid

import pytest

from app.domain.models.membership import Membership, ScopeType
from app.domain.models.membership_policy import (
    management_level,
    manages_any_unit,
    may_manage,
    role_fits_scope,
)
from app.domain.models.role import Role

D1, D2 = uuid.uuid4(), uuid.uuid4()
C1, C2 = uuid.uuid4(), uuid.uuid4()  # C1 in D1, C2 in D1


def _m(role: Role, scope_type: ScopeType, scope_id: uuid.UUID) -> Membership:
    return Membership.create(user_sub="actor", role=role, scope_type=scope_type, scope_id=scope_id)


def _level(memberships, scope_type, scope_id, district_id=D1, superadmin=False):
    return management_level(
        memberships,
        is_superadmin=superadmin,
        scope_type=scope_type,
        scope_id=scope_id,
        district_id=district_id,
    )


@pytest.mark.parametrize(
    ("role", "scope_type", "fits"),
    [
        (Role.DISTRICT_ADMIN, ScopeType.DISTRICT, True),
        (Role.DISTRICT_ADMIN, ScopeType.CONGREGATION, False),
        (Role.CONGREGATION_ADMIN, ScopeType.CONGREGATION, True),
        (Role.CONGREGATION_ADMIN, ScopeType.DISTRICT, False),
        (Role.PLANNER, ScopeType.DISTRICT, True),
        (Role.VIEWER, ScopeType.CONGREGATION, True),
    ],
)
def test_role_fits_scope(role, scope_type, fits) -> None:
    assert role_fits_scope(role, scope_type) is fits


def test_superadmin_manages_everything_without_memberships() -> None:
    assert _level([], ScopeType.DISTRICT, D2, D2, superadmin=True) == Role.DISTRICT_ADMIN
    assert manages_any_unit([], is_superadmin=True)


def test_district_admin_manages_district_and_its_congregations_only() -> None:
    actor = [_m(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, D1)]
    assert _level(actor, ScopeType.DISTRICT, D1) == Role.DISTRICT_ADMIN
    assert _level(actor, ScopeType.CONGREGATION, C1) == Role.DISTRICT_ADMIN
    assert _level(actor, ScopeType.DISTRICT, D2, D2) is None
    assert _level(actor, ScopeType.CONGREGATION, uuid.uuid4(), D2) is None


def test_congregation_admin_never_manages_district_memberships() -> None:
    actor = [_m(Role.CONGREGATION_ADMIN, ScopeType.CONGREGATION, C1)]
    assert _level(actor, ScopeType.CONGREGATION, C1) == Role.CONGREGATION_ADMIN
    assert _level(actor, ScopeType.CONGREGATION, C2) is None
    assert _level(actor, ScopeType.DISTRICT, D1) is None


@pytest.mark.parametrize(
    "memberships",
    [
        [_m(Role.PLANNER, ScopeType.DISTRICT, D1)],
        [_m(Role.VIEWER, ScopeType.CONGREGATION, C1)],
        [],
    ],
)
def test_planners_and_viewers_manage_nothing(memberships) -> None:
    assert _level(memberships, ScopeType.CONGREGATION, C1) is None
    assert not manages_any_unit(memberships, is_superadmin=False)


def test_one_unit_role_does_not_leak_into_another() -> None:
    """Admin of C1 and viewer of C2 in the same district: no rights in C2."""
    actor = [
        _m(Role.CONGREGATION_ADMIN, ScopeType.CONGREGATION, C1),
        _m(Role.VIEWER, ScopeType.CONGREGATION, C2),
    ]
    assert _level(actor, ScopeType.CONGREGATION, C2) is None
    assert manages_any_unit(actor, is_superadmin=False)


def test_ceiling_covers_new_and_existing_role() -> None:
    assert may_manage(Role.CONGREGATION_ADMIN, Role.PLANNER, Role.VIEWER)
    assert may_manage(Role.CONGREGATION_ADMIN, Role.CONGREGATION_ADMIN, None)
    assert not may_manage(Role.CONGREGATION_ADMIN, Role.PLANNER, Role.DISTRICT_ADMIN)
    assert not may_manage(Role.CONGREGATION_ADMIN, Role.DISTRICT_ADMIN)
    assert not may_manage(None, Role.VIEWER)
