# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import uuid
from types import SimpleNamespace
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
            request=SimpleNamespace(state=SimpleNamespace()),
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
                request=SimpleNamespace(state=SimpleNamespace()),
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


async def _approve_with(reg, body, district_id):
    db = AsyncMock()
    db.scalar.return_value = district_id  # every congregation belongs to the district
    cong_repo = AsyncMock()
    cong_repo.get.return_value = Congregation.create(name="G", district_id=district_id)
    reg_repo, leader_repo = AsyncMock(), AsyncMock()
    reg_repo.get.return_value = reg
    with (
        patch("app.adapters.api.routers.registrations.require_role_in_district"),
        patch("app.adapters.api.routers.registrations.get_idp_provisioner", return_value=None),
    ):
        await rr.approve_registration(
            district_id, reg.id, body, _auth(), db,
            reg_repo=reg_repo, cong_repo=cong_repo, leader_repo=leader_repo, mem_repo=AsyncMock(),
        )
    return leader_repo.save.await_args.args[0]


def _approve_body(**extra):
    district_id = extra.pop("district_id")
    return RegistrationApprove(
        role=Role.VIEWER, scope_type=ScopeType.DISTRICT, scope_id=district_id, **extra
    )


@pytest.mark.asyncio
async def test_approval_creates_the_leader_with_all_given_assignments() -> None:
    district_id, a, b = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    reg = LeaderRegistration.create(district_id=district_id, name="M", email="m@example.com")
    body = _approve_body(
        district_id=district_id,
        assignments=[
            {"congregation_id": a, "role": "Gemeindevorsteher"},
            {"congregation_id": b, "is_home": True},
        ],
    )
    leader = await _approve_with(reg, body, district_id)
    assert {(x.congregation_id, x.is_home) for x in leader.assignments} == {(a, False), (b, True)}
    assert {x.leader_id for x in leader.assignments} == {leader.id}


@pytest.mark.asyncio
async def test_approval_without_assignments_uses_the_registrants_single_choice() -> None:
    district_id, a = uuid.uuid4(), uuid.uuid4()
    reg = LeaderRegistration.create(
        district_id=district_id, name="M", email="m@example.com", congregation_id=a
    )
    leader = await _approve_with(reg, _approve_body(district_id=district_id), district_id)
    assert [(x.congregation_id, x.is_home) for x in leader.assignments] == [(a, True)]


def test_assignments_replace_the_single_choice_fields_and_need_one_home() -> None:
    from pydantic import ValidationError

    district_id, a, b = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    with pytest.raises(ValidationError):
        _approve_body(district_id=district_id, congregation_id=a, assignments=[{"congregation_id": b}])
    with pytest.raises(ValidationError):
        _approve_body(
            district_id=district_id,
            assignments=[{"congregation_id": a}, {"congregation_id": b}],
        )


def test_a_registration_role_must_fit_the_level():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RegistrationCreate(name="M", email="m@example.com", special_role="Gemeindevorsteher")
    with pytest.raises(ValidationError):
        RegistrationCreate(
            name="M", email="m@example.com", congregation_id=uuid.uuid4(), special_role="Bezirksvorsteher"
        )
    with pytest.raises(ValidationError):
        _approve_body(
            district_id=uuid.uuid4(),
            assignments=[{"congregation_id": uuid.uuid4(), "role": "Bezirksvorsteher"}],
        )


@pytest.mark.asyncio
async def test_approval_rejects_a_single_choice_whose_role_does_not_fit():
    district_id = uuid.uuid4()
    reg = LeaderRegistration.create(
        district_id=district_id, name="M", email="m@example.com",
        special_role=rr.SpecialRole.GEMEINDEVORSTEHER,  # no congregation
    )
    with pytest.raises(HTTPException) as err:
        await _approve_with(reg, _approve_body(district_id=district_id), district_id)
    assert err.value.status_code == 422


def _credentials():
    return type("Cred", (), {"credentials": "token"})()


async def _submit(credentials, claims):
    db = AsyncMock()
    request = SimpleNamespace(state=SimpleNamespace())
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    adapter = AsyncMock()
    adapter.validate_token.return_value = claims
    with patch("app.adapters.api.routers.registrations.api_deps.get_oidc_adapter", return_value=adapter):
        await rr.submit_registration(
            uuid.uuid4(),
            RegistrationCreate(name="Max", email="max@example.com"),
            db,
            request=request,
            credentials=credentials,
            district_repo=district_repo,
            reg_repo=AsyncMock(),
        )
    return db, request


@pytest.mark.asyncio
async def test_a_logged_in_registrant_is_known_to_row_level_security_before_the_insert() -> None:
    db, _ = await _submit(_credentials(), {"sub": "oidc|erika", "email": "max@example.com", "email_verified": True})

    statements = [(str(c.args[0]), c.args[1]) for c in db.execute.await_args_list]
    assert any("app.current_user_sub" in sql and params == {"sub": "oidc|erika"} for sql, params in statements)


@pytest.mark.asyncio
async def test_an_anonymous_registration_sets_no_user() -> None:
    db, _ = await _submit(None, {})

    assert not any("app.current_user_sub" in str(c.args[0]) for c in db.execute.await_args_list)


@pytest.mark.asyncio
async def test_the_validated_subject_is_the_actor_of_the_request_audit() -> None:
    """The audit middleware reads request.state.user; without it the entry looks anonymous."""
    _, request = await _submit(_credentials(), {"sub": "oidc|erika"})

    assert request.state.user.sub == "oidc|erika"


@pytest.mark.asyncio
async def test_an_anonymous_registration_has_no_actor() -> None:
    _, request = await _submit(None, {})

    assert not hasattr(request.state, "user")

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "oidc|erika", "email": "different@example.com", "email_verified": True},
        {"sub": "oidc|erika", "email": "max@example.com", "email_verified": False},
        {"sub": "oidc|erika", "email": "max@example.com", "email_verified": "true"},
        {"sub": "oidc|erika", "email": "max@example.com"},
        {"sub": "oidc|erika", "email_verified": True},
    ],
)
async def test_authenticated_registration_requires_matching_verified_email(claims) -> None:
    """Do not bind a valid subject to an email the identity provider has not verified."""
    db = AsyncMock()
    district_repo, reg_repo = AsyncMock(), AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    adapter = AsyncMock()
    adapter.validate_token.return_value = claims

    with patch("app.adapters.api.routers.registrations.api_deps.get_oidc_adapter", return_value=adapter):
        with pytest.raises(HTTPException) as exc:
            await rr.submit_registration(
                uuid.uuid4(),
                RegistrationCreate(name="Max", email="max@example.com"),
                db,
                request=SimpleNamespace(state=SimpleNamespace()),
                credentials=_credentials(),
                district_repo=district_repo,
                reg_repo=reg_repo,
            )

    assert exc.value.status_code == 403
    db.execute.assert_not_awaited()
    reg_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_verified_token_email_comparison_is_case_insensitive() -> None:
    db, request = await _submit(
        _credentials(),
        {"sub": "oidc|max", "email": "MAX@example.com", "email_verified": True},
    )
    assert request.state.user.sub == "oidc|max"
    db.execute.assert_awaited()
