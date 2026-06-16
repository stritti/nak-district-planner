"""Cross-tenant isolation tests for the RBAC permission layer.

Verifies that users from one district/tenant CANNOT access resources
from another district/tenant, and that superadmin bypass works correctly.
"""

from __future__ import annotations

import uuid

import pytest

from app.adapters.auth.permissions import (
    PermissionError,
    assert_has_role_in_congregation,
    assert_has_role_in_district,
    get_congregations_where_user_has_role,
    get_districts_where_user_has_role,
    has_role_in_congregation,
    has_role_in_district,
)
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


def _auth(memberships: list[Membership], is_superadmin: bool = False):
    """Build a minimal AuthContext-compatible object."""
    user = type("User", (), {"is_superadmin": is_superadmin})()
    return type("Auth", (), {"memberships": memberships, "user_sub": "oidc|x", "user": user})()


# ── Fixtures: two districts with congregations ──────────────────────────────

@pytest.fixture
def district_a() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def district_b() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def cong_a1(district_a: uuid.UUID) -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def cong_b1(district_b: uuid.UUID) -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def user_a_in_a(district_a: uuid.UUID) -> _auth:
    """User_A has DISTRICT_ADMIN role in District A."""
    return _auth([
        Membership.create(
            user_sub="oidc|user_a",
            role=Role.DISTRICT_ADMIN,
            scope_type=ScopeType.DISTRICT,
            scope_id=district_a,
        ),
    ])


@pytest.fixture
def user_b_in_b(district_b: uuid.UUID) -> _auth:
    """User_B has DISTRICT_ADMIN role in District B."""
    return _auth([
        Membership.create(
            user_sub="oidc|user_b",
            role=Role.DISTRICT_ADMIN,
            scope_type=ScopeType.DISTRICT,
            scope_id=district_b,
        ),
    ])


@pytest.fixture
def user_a_planner_in_a(district_a: uuid.UUID) -> _auth:
    """User_A_planner has PLANNER role in District A."""
    return _auth([
        Membership.create(
            user_sub="oidc|user_a_planner",
            role=Role.PLANNER,
            scope_type=ScopeType.DISTRICT,
            scope_id=district_a,
        ),
    ])


@pytest.fixture
def user_a_viewer_in_a(district_a: uuid.UUID) -> _auth:
    """User_A_viewer has VIEWER role in District A."""
    return _auth([
        Membership.create(
            user_sub="oidc|user_a_viewer",
            role=Role.VIEWER,
            scope_type=ScopeType.DISTRICT,
            scope_id=district_a,
        ),
    ])


@pytest.fixture
def user_no_roles() -> _auth:
    """User with no memberships at all."""
    return _auth([])


@pytest.fixture
def superadmin() -> _auth:
    """Superadmin user."""
    return _auth([], is_superadmin=True)


# ── 3.2 Cross-Tenant Read Tests ──────────────────────────────────────────────

class TestCrossTenantReadAccess:
    """Users must NOT be able to read resources from other tenants."""

    def test_user_a_cannot_read_district_b(
        self, user_a_in_a: _auth, district_b: uuid.UUID
    ) -> None:
        assert not has_role_in_district(user_a_in_a, Role.VIEWER, district_b)

    def test_user_b_cannot_read_district_a(
        self, user_b_in_b: _auth, district_a: uuid.UUID
    ) -> None:
        assert not has_role_in_district(user_b_in_b, Role.VIEWER, district_a)

    def test_user_a_assert_fails_for_district_b(
        self, user_a_in_a: _auth, district_b: uuid.UUID
    ) -> None:
        with pytest.raises(PermissionError):
            assert_has_role_in_district(user_a_in_a, Role.VIEWER, district_b)

    def test_get_districts_returns_only_own(
        self, user_a_in_a: _auth, district_a: uuid.UUID, district_b: uuid.UUID
    ) -> None:
        result = get_districts_where_user_has_role(user_a_in_a, Role.VIEWER)
        assert district_a in result
        assert district_b not in result

    def test_user_a_cannot_access_congregation_in_district_b(
        self, user_a_in_a: _auth, cong_b1: uuid.UUID
    ) -> None:
        assert not has_role_in_congregation(user_a_in_a, Role.VIEWER, cong_b1)

    def test_user_a_assert_fails_for_congregation_in_b(
        self, user_a_in_a: _auth, cong_b1: uuid.UUID
    ) -> None:
        with pytest.raises(PermissionError):
            assert_has_role_in_congregation(user_a_in_a, Role.VIEWER, cong_b1)


# ── 3.3 Cross-Tenant Write Tests ─────────────────────────────────────────────

class TestCrossTenantWriteAccess:
    """Users must NOT be able to write/modify resources from other tenants."""

    def test_user_a_cannot_write_district_b_as_planner(
        self, user_a_planner_in_a: _auth, district_b: uuid.UUID
    ) -> None:
        """Even PLANNER role in District A cannot write to District B."""
        with pytest.raises(PermissionError):
            assert_has_role_in_district(user_a_planner_in_a, Role.PLANNER, district_b)

    def test_user_a_cannot_write_district_b_as_admin(
        self, user_a_in_a: _auth, district_b: uuid.UUID
    ) -> None:
        """Even DISTRICT_ADMIN role in District A cannot write to District B."""
        with pytest.raises(PermissionError):
            assert_has_role_in_district(user_a_in_a, Role.DISTRICT_ADMIN, district_b)

    def test_user_a_cannot_delete_congregation_in_b(
        self, user_a_in_a: _auth, cong_b1: uuid.UUID
    ) -> None:
        """DISTRICT_ADMIN from A cannot assert admin rights over B's congregation."""
        with pytest.raises(PermissionError):
            assert_has_role_in_congregation(user_a_in_a, Role.CONGREGATION_ADMIN, cong_b1)

    def test_user_no_roles_cannot_write_anything(
        self, user_no_roles: _auth, district_a: uuid.UUID
    ) -> None:
        with pytest.raises(PermissionError):
            assert_has_role_in_district(user_no_roles, Role.VIEWER, district_a)


# ── 3.4 Admin Sonderrechte Tests ─────────────────────────────────────────────

class TestSuperadminCrossTenantAccess:
    """Superadmin MUST be able to bypass all tenant boundaries."""

    def test_superadmin_can_read_any_district(
        self, superadmin: _auth, district_a: uuid.UUID, district_b: uuid.UUID
    ) -> None:
        assert has_role_in_district(superadmin, Role.VIEWER, district_a)
        assert has_role_in_district(superadmin, Role.VIEWER, district_b)

    def test_superadmin_can_write_any_district(
        self, superadmin: _auth, district_a: uuid.UUID
    ) -> None:
        assert has_role_in_district(superadmin, Role.DISTRICT_ADMIN, district_a)

    def test_superadmin_can_access_any_congregation(
        self, superadmin: _auth, cong_a1: uuid.UUID, cong_b1: uuid.UUID
    ) -> None:
        assert has_role_in_congregation(superadmin, Role.DISTRICT_ADMIN, cong_a1)
        assert has_role_in_congregation(superadmin, Role.DISTRICT_ADMIN, cong_b1)

    def test_superadmin_assert_passes_anywhere(
        self, superadmin: _auth, district_a: uuid.UUID, cong_b1: uuid.UUID
    ) -> None:
        # Should not raise
        assert_has_role_in_district(superadmin, Role.DISTRICT_ADMIN, district_a)
        assert_has_role_in_congregation(superadmin, Role.CONGREGATION_ADMIN, cong_b1)


# ── 3.5 Parametrisierte Tests über alle Rollen ───────────────────────────────

class TestCrossTenantAllRoles:
    """Every role must respect tenant boundaries."""

    @pytest.mark.parametrize(
        "role", [Role.VIEWER, Role.PLANNER, Role.CONGREGATION_ADMIN, Role.DISTRICT_ADMIN]
    )
    def test_no_role_can_cross_tenant_boundary(
        self, role: Role, district_a: uuid.UUID, district_b: uuid.UUID
    ) -> None:
        """A user with ANY role in District A cannot assert that role in District B."""
        user_in_a = _auth([
            Membership.create(
                user_sub="oidc|x",
                role=role,
                scope_type=ScopeType.DISTRICT,
                scope_id=district_a,
            ),
        ])
        # District B access must be denied for all roles
        assert not has_role_in_district(user_in_a, role, district_b)

    @pytest.mark.parametrize(
        "role", [Role.VIEWER, Role.PLANNER, Role.CONGREGATION_ADMIN, Role.DISTRICT_ADMIN]
    )
    def test_cross_tenant_congregation_blocked_for_all_roles(
        self, role: Role, district_a: uuid.UUID, cong_b1: uuid.UUID
    ) -> None:
        """A user with ANY role cannot access a congregation in another district."""
        user_in_a = _auth([
            Membership.create(
                user_sub="oidc|x",
                role=role,
                scope_type=ScopeType.DISTRICT,
                scope_id=district_a,
            ),
        ])
        assert not has_role_in_congregation(user_in_a, role, cong_b1)

    @pytest.mark.parametrize(
        "role", [Role.VIEWER, Role.PLANNER]
    )
    def test_lower_roles_cannot_assert_higher_role_in_own_tenant(
        self, role: Role, district_a: uuid.UUID
    ) -> None:
        """A user with a lower role cannot assert a higher role, even in their own tenant."""
        user_in_a = _auth([
            Membership.create(
                user_sub="oidc|x",
                role=role,
                scope_type=ScopeType.DISTRICT,
                scope_id=district_a,
            ),
        ])
        assert not has_role_in_district(user_in_a, Role.DISTRICT_ADMIN, district_a)


# ── Congregation-level scoping ───────────────────────────────────────────────

class TestCongregationLevelScoping:
    """CONGREGATION_ADMIN must be limited to their own congregation."""

    def test_congregation_admin_own_congregation(
        self, cong_a1: uuid.UUID
    ) -> None:
        user = _auth([
            Membership.create(
                user_sub="oidc|x",
                role=Role.CONGREGATION_ADMIN,
                scope_type=ScopeType.CONGREGATION,
                scope_id=cong_a1,
            ),
        ])
        assert has_role_in_congregation(user, Role.CONGREGATION_ADMIN, cong_a1)

    def test_congregation_admin_cannot_access_other_congregation(
        self, cong_a1: uuid.UUID, cong_b1: uuid.UUID
    ) -> None:
        user = _auth([
            Membership.create(
                user_sub="oidc|x",
                role=Role.CONGREGATION_ADMIN,
                scope_type=ScopeType.CONGREGATION,
                scope_id=cong_a1,
            ),
        ])
        assert not has_role_in_congregation(user, Role.VIEWER, cong_b1)

    def test_congregation_admin_cannot_access_district_level(
        self, cong_a1: uuid.UUID, district_a: uuid.UUID
    ) -> None:
        """CONGREGATION_ADMIN has no district-level authority."""
        user = _auth([
            Membership.create(
                user_sub="oidc|x",
                role=Role.CONGREGATION_ADMIN,
                scope_type=ScopeType.CONGREGATION,
                scope_id=cong_a1,
            ),
        ])
        assert not has_role_in_district(user, Role.VIEWER, district_a)

    def test_congregation_admin_get_congregations_own_only(
        self, cong_a1: uuid.UUID, cong_b1: uuid.UUID
    ) -> None:
        user = _auth([
            Membership.create(
                user_sub="oidc|x",
                role=Role.CONGREGATION_ADMIN,
                scope_type=ScopeType.CONGREGATION,
                scope_id=cong_a1,
            ),
        ])
        congregations = get_congregations_where_user_has_role(user, Role.VIEWER)
        assert cong_a1 in congregations
        assert cong_b1 not in congregations
