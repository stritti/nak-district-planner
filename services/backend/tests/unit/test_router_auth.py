from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.adapters.api.routers import auth as r
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


@pytest.mark.asyncio
async def test_get_current_user_info_maps_authenticated_user_fields() -> None:
    user = SimpleNamespace(
        sub="user-sub",
        email="test@example.org",
        username="tester",
        name="Test User",
        given_name="Test",
        family_name="User",
        is_superadmin=True,
    )

    out = await r.get_current_user_info(user)

    assert out.sub == "user-sub"
    assert out.email == "test@example.org"
    assert out.is_superadmin is True


@pytest.mark.asyncio
async def test_get_access_context_for_memberships_and_pending_approval() -> None:
    district_id = uuid.uuid4()
    auth_with_memberships = SimpleNamespace(
        user=SimpleNamespace(is_superadmin=False),
        memberships=[
            Membership.create(
                user_sub="user-sub",
                role=Role.PLANNER,
                scope_type=ScopeType.DISTRICT,
                scope_id=district_id,
            )
        ],
    )

    out_active = await r.get_access_context(auth_with_memberships)
    assert out_active.status == "ACTIVE"
    assert out_active.memberships[0].scope_id == str(district_id)

    auth_pending = SimpleNamespace(user=SimpleNamespace(is_superadmin=False), memberships=[])
    out_pending = await r.get_access_context(auth_pending)
    assert out_pending.status == "PENDING_APPROVAL"
    assert out_pending.memberships == []
