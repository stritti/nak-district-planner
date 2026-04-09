from __future__ import annotations

import uuid
from datetime import datetime, timezone
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

    with (
        patch("app.adapters.api.routers.registrations.SqlDistrictRepository") as district_repo_cls,
        patch(
            "app.adapters.api.routers.registrations.SqlLeaderRegistrationRepository"
        ) as reg_repo_cls,
        patch("app.adapters.api.routers.registrations.api_deps.get_oidc_adapter") as get_adapter,
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo

        reg_repo = AsyncMock()
        reg_repo_cls.return_value = reg_repo

        out = await rr.submit_registration(
            district_id,
            RegistrationCreate(name="Max", email="max@example.com"),
            db,
            credentials=None,
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
            )
        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_list_registrations_and_pending_overview() -> None:
    district_id = uuid.uuid4()
    reg = LeaderRegistration.create(district_id=district_id, name="M", email="m@example.com")
    db = AsyncMock()
    auth = _auth(is_superadmin=True)

    with (
        patch("app.adapters.api.routers.registrations.assert_has_role_in_district"),
        patch("app.adapters.api.routers.registrations.SqlDistrictRepository") as district_repo_cls,
        patch(
            "app.adapters.api.routers.registrations.SqlLeaderRegistrationRepository"
        ) as reg_repo_cls,
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo.list_all.return_value = [District.create(name="D")]
        district_repo_cls.return_value = district_repo

        reg_repo = AsyncMock()
        reg_repo.list_by_district.return_value = [reg]
        reg_repo.count_by_district.return_value = 2
        reg_repo_cls.return_value = reg_repo

        rows = await rr.list_registrations(district_id, auth, db)
        ov = await rr.get_pending_overview(auth, db)

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
    auth = _auth()

    with (
        patch("app.adapters.api.routers.registrations.assert_has_role_in_district"),
        patch(
            "app.adapters.api.routers.registrations.SqlLeaderRegistrationRepository"
        ) as reg_repo_cls,
        patch("app.adapters.api.routers.registrations.SqlCongregationRepository") as cong_repo_cls,
        patch("app.adapters.api.routers.registrations.SqlLeaderRepository") as leader_repo_cls,
        patch("app.adapters.api.routers.registrations.SqlMembershipRepository") as mem_repo_cls,
        patch(
            "app.adapters.api.routers.registrations.get_idp_provisioner",
            return_value=None,
        ),
    ):
        reg_repo = AsyncMock()
        reg_repo.get.return_value = reg
        reg_repo_cls.return_value = reg_repo

        cong_repo = AsyncMock()
        cong_repo.get.return_value = Congregation.create(name="G", district_id=district_id)
        cong_repo_cls.return_value = cong_repo

        leader_repo_cls.return_value = AsyncMock()
        mem_repo_cls.return_value = AsyncMock()

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
        )
        assert rejected.status == RegistrationStatus.REJECTED

        # delete existing
        await rr.delete_registration(district_id, reg.id, auth, db)


@pytest.mark.asyncio
async def test_approve_provisioning_failure_sets_status() -> None:
    district_id = uuid.uuid4()
    reg = LeaderRegistration.create(district_id=district_id, name="M", email="m@example.com")
    db = AsyncMock()
    auth = _auth()

    provisioner = AsyncMock()
    provisioner.provision_user.side_effect = rr.IdpProvisioningError("boom")

    with (
        patch("app.adapters.api.routers.registrations.assert_has_role_in_district"),
        patch(
            "app.adapters.api.routers.registrations.SqlLeaderRegistrationRepository"
        ) as reg_repo_cls,
        patch("app.adapters.api.routers.registrations.SqlLeaderRepository") as leader_repo_cls,
        patch("app.adapters.api.routers.registrations.SqlMembershipRepository") as mem_repo_cls,
        patch(
            "app.adapters.api.routers.registrations.get_idp_provisioner",
            return_value=provisioner,
        ),
    ):
        reg_repo = AsyncMock()
        reg_repo.get.return_value = reg
        reg_repo_cls.return_value = reg_repo
        leader_repo_cls.return_value = AsyncMock()
        mem_repo_cls.return_value = AsyncMock()

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
        )

    assert out.idp_provision_status == "FAILED"
