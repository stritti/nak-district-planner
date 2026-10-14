# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Locked and versioned leader inline mutation regressions."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
    {"rank": "Pr."}, {"is_active": False},
    {"congregation_id": str(uuid.uuid4())}, {"notes": "x"},
])
async def test_status_and_scope_changes_not_exposed_inline(payload):
    ctx = _setup()
    with pytest.raises(ValidationError):
        leaders.LeaderInlineUpdate.model_validate(payload)
    ctx[2].save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    leaders.LeaderInlineUpdate(name=None),
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
