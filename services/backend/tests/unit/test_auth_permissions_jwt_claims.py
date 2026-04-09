from __future__ import annotations

import uuid

import pytest

from app.adapters.auth import jwt_claims
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
    user = type("User", (), {"is_superadmin": is_superadmin})()
    return type("Auth", (), {"memberships": memberships, "user_sub": "oidc|x", "user": user})()


def test_permissions_happy_paths_and_hierarchy() -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    memberships = [
        Membership.create(
            user_sub="oidc|x",
            role=Role.DISTRICT_ADMIN,
            scope_type=ScopeType.DISTRICT,
            scope_id=district_id,
        ),
        Membership.create(
            user_sub="oidc|x",
            role=Role.PLANNER,
            scope_type=ScopeType.CONGREGATION,
            scope_id=congregation_id,
        ),
    ]
    auth = _auth(memberships)
    assert has_role_in_district(auth, Role.VIEWER, district_id)
    assert has_role_in_congregation(auth, Role.VIEWER, congregation_id)
    assert district_id in get_districts_where_user_has_role(auth, Role.VIEWER)
    assert congregation_id in get_congregations_where_user_has_role(auth, Role.VIEWER)


def test_permissions_superadmin_and_denied_paths() -> None:
    district_id = uuid.uuid4()
    auth_super = _auth([], is_superadmin=True)
    assert has_role_in_district(auth_super, Role.DISTRICT_ADMIN, district_id)
    assert has_role_in_congregation(auth_super, Role.DISTRICT_ADMIN, uuid.uuid4())

    auth = _auth([])
    assert not has_role_in_district(auth, Role.VIEWER, district_id)
    assert not has_role_in_congregation(auth, Role.VIEWER, uuid.uuid4())
    with pytest.raises(PermissionError):
        assert_has_role_in_district(auth, Role.VIEWER, district_id)
    with pytest.raises(PermissionError):
        assert_has_role_in_congregation(auth, Role.VIEWER, uuid.uuid4())


def test_extract_memberships_from_claims_variants() -> None:
    district_id = uuid.uuid4()
    valid = {
        "sub": "oidc|u1",
        "memberships": [
            {"role": "PLANNER", "scope_type": "DISTRICT", "scope_id": str(district_id)}
        ],
    }
    out = jwt_claims.extract_memberships_from_claims(valid)
    assert len(out) == 1
    assert out[0].scope_id == district_id

    assert jwt_claims.extract_memberships_from_claims({}) == []
    assert jwt_claims.extract_memberships_from_claims({"memberships": "bad"}) == []

    mixed = {
        "sub": "oidc|u2",
        "memberships": [
            "nope",
            {"role": "BAD", "scope_type": "DISTRICT", "scope_id": str(uuid.uuid4())},
            {"role": "VIEWER", "scope_type": "NOPE", "scope_id": str(uuid.uuid4())},
            {"role": "VIEWER", "scope_type": "DISTRICT", "scope_id": "not-uuid"},
            {"role": "VIEWER", "scope_type": "DISTRICT", "scope_id": str(uuid.uuid4())},
        ],
    }
    out2 = jwt_claims.extract_memberships_from_claims(mixed)
    assert len(out2) == 1
