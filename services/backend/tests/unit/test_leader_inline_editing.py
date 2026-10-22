# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Locked and versioned leader inline mutation regressions."""

import uuid
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.routers import leaders
from app.adapters.api.schemas.leader import LeaderUpdate
from app.domain.models.leader import Leader
from app.domain.models.role import Role


def _setup():
    district_id = uuid.uuid4()
    leader = Leader.create(name="Anna", district_id=district_id, email="old@example.org")
    repo = AsyncMock()
    repo.get_for_update.return_value = leader
    auth = SimpleNamespace(user=SimpleNamespace(is_superadmin=True), memberships=[])
    return district_id, leader, repo, auth


async def _inline(ctx, body, revision):
    district_id, leader, repo, auth = ctx
    with patch.object(leaders, "require_role_in_district") as check:
        result = await leaders.inline_update_leader(
            district_id, leader.id, body, auth, AsyncMock(),
            if_match=revision, leaders_repo=repo,
        )
    check.assert_called_once_with(auth, Role.PLANNER, district_id)
    return result


@pytest.mark.asyncio
async def test_name_mutation_returns_fresh_strong_revision():
    ctx = _setup()
    previous = leaders._leader_revision(ctx[1])
    result = await _inline(ctx, LeaderUpdate(name="Anna Neu"), previous)
    assert result.name == "Anna Neu"
    assert result.revision != previous
    ctx[2].get_for_update.assert_awaited_once_with(ctx[1].id)
    ctx[2].save.assert_awaited_once()


@pytest.mark.asyncio
async def test_optional_contact_fields_can_be_cleared():
    ctx = _setup()
    result = await _inline(ctx, LeaderUpdate(email=None), leaders._leader_revision(ctx[1]))
    assert result.email is None


@pytest.mark.asyncio
async def test_missing_revision_rejected_without_accessing_row():
    ctx = _setup()
    with pytest.raises(HTTPException) as err:
        await _inline(ctx, LeaderUpdate(phone="123"), None)
    assert err.value.status_code == 428
    ctx[2].get_for_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_revision_preserves_existing_contact():
    ctx = _setup()
    with pytest.raises(HTTPException) as err:
        await _inline(ctx, LeaderUpdate(email="new@example.org"), '"old"')
    assert err.value.status_code == 412
    assert ctx[1].email == "old@example.org"
    ctx[2].save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"notes": "x"}, {"user_sub": "sub"}, {"hidden_from_lists": True},
    {"service_end_date": "2030-01-01"}, {"rank": "Kaiser"}, {"special_role": "Chef"},
])
async def test_workflow_and_unknown_fields_not_exposed_inline(payload):
    ctx = _setup()
    with pytest.raises(ValidationError):
        leaders.LeaderInlineUpdate.model_validate(payload)
    ctx[2].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_rank_can_be_changed():
    ctx = _setup()
    result = await _inline(ctx, leaders.LeaderInlineUpdate(rank="Pr."), leaders._leader_revision(ctx[1]))
    assert result.rank == "Pr."


@pytest.mark.parametrize("field", ["special_role", "congregation_id"])
def test_assignment_fields_are_no_longer_inline_editable(field):
    with pytest.raises(ValidationError):
        leaders.LeaderInlineUpdate.model_validate({field: None})


@pytest.mark.asyncio
async def test_activity_change_requires_district_admin_and_keeps_lock_order():
    ctx = _setup()
    district_id, leader, repo, auth = ctx

    def guard(_auth, role, _district):
        if role is Role.DISTRICT_ADMIN:
            raise HTTPException(403, "Keine Berechtigung")

    with (
        patch.object(leaders, "require_role_in_district", side_effect=guard),
        patch.object(leaders, "acquire_advisory_xact_lock", new=AsyncMock()) as lock,
        pytest.raises(HTTPException) as err,
    ):
        await leaders.inline_update_leader(
            district_id, leader.id,
            leaders.LeaderInlineUpdate(is_active=False, confirm_deactivation=True),
            auth, AsyncMock(),
            if_match=leaders._leader_revision(leader), leaders_repo=repo,
        )
    assert err.value.status_code == 403
    lock.assert_awaited_once()
    assert leader.is_active is True
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_district_admin_can_deactivate_inline():
    ctx = _setup()
    district_id, leader, repo, auth = ctx
    with (
        patch.object(leaders, "require_role_in_district"),
        patch.object(leaders, "acquire_advisory_xact_lock", new=AsyncMock()),
    ):
        result = await leaders.inline_update_leader(
            district_id, leader.id,
            leaders.LeaderInlineUpdate(is_active=False, confirm_deactivation=True),
            auth, AsyncMock(),
            if_match=leaders._leader_revision(leader), leaders_repo=repo,
        )
    assert result.is_active is False


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    leaders.LeaderInlineUpdate(name=None),
    leaders.LeaderInlineUpdate(rank=None),
    leaders.LeaderInlineUpdate(is_active=None),
    leaders.LeaderInlineUpdate(),
])
async def test_invalid_inline_leader_payloads_are_never_mutated(payload):
    ctx = _setup()
    with pytest.raises(HTTPException) as err:
        await _inline(ctx, payload, leaders._leader_revision(ctx[1]))
    assert err.value.status_code == 422
    ctx[2].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_cross_district_record_is_indistinguishable_from_absent_record():
    ctx = _setup()
    ctx[1].district_id = uuid.uuid4()
    with pytest.raises(HTTPException) as err:
        await _inline(ctx, LeaderUpdate(name="Neue"), leaders._leader_revision(ctx[1]))
    assert err.value.status_code == 404
    ctx[2].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_permission_denied_and_never_saved():
    ctx = _setup()
    with (
        patch.object(leaders, "require_role_in_district", side_effect=HTTPException(403)),
        pytest.raises(HTTPException) as err,
    ):
        await leaders.inline_update_leader(
            ctx[0], ctx[1].id, LeaderUpdate(name="Neue"), ctx[3], AsyncMock(),
            if_match=leaders._leader_revision(ctx[1]), leaders_repo=ctx[2],
        )
    assert err.value.status_code == 403
    ctx[2].save.assert_not_awaited()


@pytest.mark.parametrize("payload", [
    {"name": "X" * 256},
    {"email": "x" * 256},
    {"phone": "1" * 101},
])
def test_inline_contact_length_rejected_before_database_write(payload):
    with pytest.raises(ValidationError):
        leaders.LeaderInlineUpdate.model_validate(payload)


@pytest.mark.parametrize("payload", [
    {"name": "X" * 255},
    {"email": "x" * 255},
    {"phone": "1" * 100},
])
def test_inline_contact_length_boundary_is_accepted(payload):
    assert leaders.LeaderInlineUpdate.model_validate(payload).model_fields_set == set(payload)


@pytest.mark.asyncio
async def test_direct_deactivation_without_confirmation_is_rejected_before_any_write():
    ctx = _setup()
    district_id, leader, repo, auth = ctx
    with (
        patch.object(leaders, "require_role_in_district"),
        patch.object(leaders, "acquire_advisory_xact_lock", new=AsyncMock()) as lock,
        pytest.raises(HTTPException) as err,
    ):
        await leaders.inline_update_leader(
            district_id, leader.id, leaders.LeaderInlineUpdate(is_active=False), auth, AsyncMock(),
            if_match=leaders._leader_revision(leader), leaders_repo=repo,
        )
    assert err.value.status_code == 409
    assert err.value.detail["code"] == "deactivation_unconfirmed"
    assert leader.is_active is True
    repo.get_for_update.assert_not_awaited()
    repo.save.assert_not_awaited()
    lock.assert_not_awaited()


@pytest.mark.asyncio
async def test_reactivation_and_other_fields_need_no_confirmation():
    ctx = _setup()
    district_id, leader, repo, auth = ctx
    leader.is_active = False
    with (
        patch.object(leaders, "require_role_in_district"),
        patch.object(leaders, "acquire_advisory_xact_lock", new=AsyncMock()),
    ):
        result = await leaders.inline_update_leader(
            district_id, leader.id, leaders.LeaderInlineUpdate(is_active=True), auth, AsyncMock(),
            if_match=leaders._leader_revision(leader), leaders_repo=repo,
        )
    assert result.is_active is True


def test_confirmation_flag_is_not_a_persisted_leader_field():
    body = leaders.LeaderInlineUpdate(is_active=False, confirm_deactivation=True)
    assert "confirm_deactivation" not in leaders.LeaderUpdate.model_validate(
        body.model_dump(exclude_unset=True, exclude={"confirm_deactivation"})
    ).model_fields_set
