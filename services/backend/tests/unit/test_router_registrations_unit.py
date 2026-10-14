# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import registrations as rr
from app.adapters.api.schemas.registration import (
    RegistrationApprove,
    RegistrationCreate,
    RegistrationReject,
)
from app.adapters.auth.oidc import TokenValidationError
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.leader_registration import LeaderRegistration, RegistrationStatus
from app.domain.models.membership import ScopeType
from app.domain.models.role import Role


def _auth(is_superadmin: bool = False):
    user = type("User", (), {"is_superadmin": is_superadmin})()
    return type("Auth", (), {"memberships": [], "user_sub": "oidc|admin", "user": user})()


@pytest.mark.asyncio
async def test_submit_registration_paths() -> None:
    district_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.adapters.api.routers.registrations.api_deps.get_oidc_adapter") as get_adapter:
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")

        reg_repo = AsyncMock()

        out = await rr.submit_registration(
            district_id,
            RegistrationCreate(name="Max", email="max@example.com"),
            db,
            credentials=None,
            district_repo=district_repo,
            reg_repo=reg_repo,
        )
        assert out.name == "Max"

        adapter = AsyncMock()
        adapter.validate_token.side_effect = TokenValidationError("bad")
        get_adapter.return_value = adapter
        with pytest.raises(HTTPException) as exc:
            await rr.submit_registration(
                district_id,
                RegistrationCreate(name="Max", email="max@example.com"),
                db,
                credentials=type("Cred", (), {"credentials": "bad"})(),
                district_repo=district_repo,
                reg_repo=reg_repo,
            )
        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_list_registrations_and_pending_overview() -> None:
    district_id = uuid.uuid4()
    reg = LeaderRegistration.create(district_id=district_id, name="M", email="m@example.com")
    db = AsyncMock()
    auth = _auth(is_superadmin=True)

    with patch("app.adapters.api.routers.registrations.require_role_in_district"):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo.list_all.return_value = [District.create(name="D")]

        reg_repo = AsyncMock()
        reg_repo.list_by_district.return_value = [reg]
        reg_repo.count_by_district.return_value = 2

        rows = await rr.list_registrations(
            district_id, auth, db, district_repo=district_repo, reg_repo=reg_repo
        )
        ov = await rr.get_pending_overview(auth, db, district_repo=district_repo, reg_repo=reg_repo)

    assert len(rows) == 1
    assert ov.total_pending == 2


@pytest.mark.asyncio
async def test_approve_reject_delete_paths() -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    reg = LeaderRegistration.create(
        district_id=district_id,
        name="M",
        email="m@example.com",
    )
    db = AsyncMock()
    db.scalar.return_value = district_id  # congregation_id belongs to the district
    auth = _auth()

    with (
        patch("app.adapters.api.routers.registrations.require_role_in_district"),
        patch(
            "app.adapters.api.routers.registrations.get_idp_provisioner",
            return_value=None,
        ),
    ):
        reg_repo = AsyncMock()
        reg_repo.get.return_value = reg

        cong_repo = AsyncMock()
        cong_repo.get.return_value = Congregation.create(name="G", district_id=district_id)

        leader_repo = AsyncMock()
        mem_repo = AsyncMock()

        approved = await rr.approve_registration(
            district_id,
            reg.id,
            RegistrationApprove(
                role=Role.PLANNER,
                scope_type=ScopeType.CONGREGATION,
                scope_id=congregation_id,
                congregation_id=congregation_id,
            ),
            auth,
            db,
            reg_repo=reg_repo,
            cong_repo=cong_repo,
            leader_repo=leader_repo,
            mem_repo=mem_repo,
        )
        assert approved.status == RegistrationStatus.APPROVED

        # reject conflict for non-pending
        with pytest.raises(HTTPException) as exc:
            await rr.reject_registration(
                district_id,
                reg.id,
                RegistrationReject(reason="x"),
                auth,
                db,
                reg_repo=reg_repo,
            )
        assert exc.value.status_code == 409

        # reset and reject works
        reg.status = RegistrationStatus.PENDING
        rejected = await rr.reject_registration(
            district_id,
            reg.id,
            RegistrationReject(reason="x"),
            auth,
            db,
            reg_repo=reg_repo,
        )
        assert rejected.status == RegistrationStatus.REJECTED

        # delete existing
        await rr.delete_registration(district_id, reg.id, auth, db, reg_repo=reg_repo)


@pytest.mark.asyncio
async def test_approve_provisioning_failure_sets_status() -> None:
    district_id = uuid.uuid4()
    reg = LeaderRegistration.create(district_id=district_id, name="M", email="m@example.com")
    db = AsyncMock()
    auth = _auth()

    provisioner = AsyncMock()
    provisioner.provision_user.side_effect = rr.IdpProvisioningError("boom")

    with (
        patch("app.adapters.api.routers.registrations.require_role_in_district"),
        patch(
            "app.adapters.api.routers.registrations.get_idp_provisioner",
            return_value=provisioner,
        ),
    ):
        reg_repo = AsyncMock()
        reg_repo.get.return_value = reg
        leader_repo = AsyncMock()
        mem_repo = AsyncMock()

        out = await rr.approve_registration(
            district_id,
            reg.id,
            RegistrationApprove(
                role=Role.PLANNER,
                scope_type=ScopeType.DISTRICT,
                scope_id=district_id,
            ),
            auth,
            db,
            reg_repo=reg_repo,
            cong_repo=AsyncMock(),
            leader_repo=leader_repo,
            mem_repo=mem_repo,
        )

    assert out.idp_provision_status == "FAILED"
