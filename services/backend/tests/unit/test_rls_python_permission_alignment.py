# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Drift detection between SQL RLS authorization and Python permission guards."""

import pytest

from app.adapters.auth.permissions import has_role_in_district
from app.adapters.db.migrations import event_duty_rls, rls_policies
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import PRIVILEGE_ORDER, Role, roles_at_least, roles_at_least_sql


def _auth(memberships, *, superadmin=False):
    return type(
        "AuthContext",
        (),
        {
            "user_sub": "user-sub",
            "memberships": tuple(memberships),
            "user": type("User", (), {"is_superadmin": superadmin})(),
        },
    )()


def _membership(role, scope_type, scope_id):
    return Membership.create(
        user_sub="user-sub",
        role=role,
        scope_type=scope_type,
        scope_id=scope_id,
    )


def test_privilege_order_covers_all_roles():
    assert set(PRIVILEGE_ORDER) == set(Role)
    assert len(PRIVILEGE_ORDER) == len(Role)


def test_roles_at_least_matches_role_hierarchy():
    assert roles_at_least(Role.VIEWER) == PRIVILEGE_ORDER
    assert roles_at_least(Role.PLANNER) == (
        Role.DISTRICT_ADMIN,
        Role.CONGREGATION_ADMIN,
        Role.PLANNER,
    )
    assert roles_at_least(Role.CONGREGATION_ADMIN) == (
        Role.DISTRICT_ADMIN,
        Role.CONGREGATION_ADMIN,
    )
    assert roles_at_least(Role.DISTRICT_ADMIN) == (Role.DISTRICT_ADMIN,)


def test_sql_role_literals_match_python_guards():
    assert roles_at_least_sql(Role.PLANNER) == "'DISTRICT_ADMIN','CONGREGATION_ADMIN','PLANNER'"
    assert (
        roles_at_least_sql(Role.VIEWER)
        == "'DISTRICT_ADMIN','CONGREGATION_ADMIN','PLANNER','VIEWER'"
    )
    assert (
        roles_at_least_sql(Role.CONGREGATION_ADMIN) == "'DISTRICT_ADMIN','CONGREGATION_ADMIN'"
    )


def test_generated_rls_sql_uses_derived_role_sets():
    district_write = rls_policies.district_write_membership_sql("t")
    congregation_write = rls_policies.congregation_write_membership_sql("t")
    assert roles_at_least_sql(Role.PLANNER) in district_write
    assert roles_at_least_sql(Role.PLANNER) in congregation_write
    assert "'PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN'" not in district_write

    scope_read = event_duty_rls._scope("t")
    assert roles_at_least_sql(Role.VIEWER) in scope_read
    scope_write = event_duty_rls._scope("t", roles=roles_at_least_sql(Role.PLANNER))
    assert roles_at_least_sql(Role.PLANNER) in scope_write


@pytest.mark.parametrize("threshold", list(Role))
def test_sql_and_python_accept_same_role_sets(threshold):
    """Every role accepted by a generated RLS set passes the matching guard."""
    district_id = "11111111-1111-1111-1111-111111111111"
    congregation_id = "22222222-2222-2222-2222-222222222222"
    for role in Role:
        sql_roles = roles_at_least(threshold)

        district_membership = _membership(role, ScopeType.DISTRICT, district_id)
        assert (district_membership.role in sql_roles) == has_role_in_district(
            _auth([district_membership]), threshold, district_id
        ), f"drift for {role.value} / DISTRICT at {threshold.value}"

        congregation_membership = _membership(
            role, ScopeType.CONGREGATION, congregation_id
        )
        assert (congregation_membership.role in sql_roles) == has_role_in_district(
            _auth([congregation_membership]),
            threshold,
            district_id,
            {congregation_id},
        ), f"drift for {role.value} / CONGREGATION at {threshold.value}"


def test_admin_policies_require_congregation_admin_or_higher():
    admin_sql = event_duty_rls._admin("t")
    assert roles_at_least_sql(Role.CONGREGATION_ADMIN) in admin_sql
    assert roles_at_least_sql(Role.CONGREGATION_ADMIN) == "'DISTRICT_ADMIN','CONGREGATION_ADMIN'"


def test_eligible_duty_users_actor_check_uses_planner_or_higher():
    eligible = next(sql for sql in event_duty_rls._FUNCTIONS if "eligible_duty_users" in sql)
    assert roles_at_least_sql(Role.PLANNER) in eligible
