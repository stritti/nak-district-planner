# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Behavioral coverage of absence CRUD: RBAC, tenant boundary, validation and failures."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.routers import leader_unavailabilities as router
from app.adapters.api.schemas.leader_unavailability import (
    LeaderUnavailabilityCreate,
    LeaderUnavailabilityUpdate,
)
from app.domain.models.leader_unavailability import (
    LeaderUnavailability,
    UnavailabilityReason,
)
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.role import Role


@pytest.fixture
def district_id() -> uuid.UUID:
    return uuid.uuid4()


def _auth(district: uuid.UUID, role: Role = Role.PLANNER) -> SimpleNamespace:
    return SimpleNamespace(
        user_sub="operator",
        user=SimpleNamespace(is_superadmin=False),
        memberships=[
            Membership.create(
                user_sub="operator",
                role=role,
                scope_type=ScopeType.DISTRICT,
                scope_id=district,
            )
        ],
    )


def _period(leader_id: uuid.UUID) -> LeaderUnavailability:
    start = datetime(2026, 11, 2, 12, tzinfo=UTC)
    return LeaderUnavailability.create(
        leader_id=leader_id,
        start_at=start,
        end_at=start + timedelta(days=1),
        reason=UnavailabilityReason.VACATION,
        note="Urlaub",
    )


def _repos(district: uuid.UUID, leader_id: uuid.UUID) -> tuple[AsyncMock, AsyncMock]:
    leaders = AsyncMock()
    leaders.get.return_value = SimpleNamespace(id=leader_id, district_id=district)
    leaders.list_by_district.return_value = [SimpleNamespace(id=leader_id, district_id=district)]
    repo = AsyncMock()
    repo.list_by_leader.return_value = [_period(leader_id)]
    repo.get.return_value = _period(leader_id)
    return leaders, repo


@pytest.mark.asyncio
async def test_list_absences_scoped_and_ordered(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    extra_leader = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    leaders.list_by_district.return_value = [
        SimpleNamespace(id=leader_id, district_id=district_id),
        SimpleNamespace(id=extra_leader, district_id=district_id),
    ]
    early = _period(leader_id)
    late = _period(extra_leader)
    late.start_at += timedelta(days=3)
    repo.list_by_leader.side_effect = lambda key: [late] if key == extra_leader else [early]

    result = await router.list_unavailabilities(
        district_id, _auth(district_id), AsyncMock(), leaders=leaders, repo=repo
    )

    assert [row.id for row in result] == [early.id, late.id]
    assert repo.list_by_leader.await_count == 2
    assert result[0].note == "Urlaub"


@pytest.mark.asyncio
async def test_list_for_one_leader_and_empty_list(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    repo.list_by_leader.return_value = []

    result = await router.list_unavailabilities(
        district_id, _auth(district_id, Role.VIEWER), AsyncMock(),
        leader_id=leader_id, leaders=leaders, repo=repo,
    )

    assert result == []
    repo.list_by_leader.assert_awaited_once_with(leader_id)
    leaders.list_by_district.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign", [False, True])
async def test_filter_cannot_read_unknown_or_foreign_leader(
    district_id: uuid.UUID, foreign: bool
) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    leaders.get.return_value = (
        SimpleNamespace(id=leader_id, district_id=uuid.uuid4()) if foreign else None
    )

    with pytest.raises(HTTPException) as error:
        await router.list_unavailabilities(
            district_id, _auth(district_id), AsyncMock(),
            leader_id=leader_id, leaders=leaders, repo=repo,
        )

    assert error.value.status_code == 404
    repo.list_by_leader.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_requires_district_viewer(district_id: uuid.UUID) -> None:
    leaders, repo = _repos(district_id, uuid.uuid4())
    with pytest.raises(HTTPException) as error:
        await router.list_unavailabilities(
            district_id, _auth(uuid.uuid4(), Role.DISTRICT_ADMIN),
            AsyncMock(), leaders=leaders, repo=repo,
        )
    assert error.value.status_code == 403
    leaders.list_by_district.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_unavailability_saves_and_preserves_notes(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    item = _period(leader_id)
    body = LeaderUnavailabilityCreate(
        leader_id=leader_id,
        start_at=item.start_at,
        end_at=item.end_at,
        reason=item.reason,
        note="Abwesend",
    )

    result = await router.create_unavailability(
        district_id, body, _auth(district_id), AsyncMock(), leaders=leaders, repo=repo
    )

    assert result.leader_id == leader_id
    assert result.note == "Abwesend"
    repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_rejects_foreign_leader_before_write(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    leaders.get.return_value = SimpleNamespace(id=leader_id, district_id=uuid.uuid4())
    item = _period(leader_id)
    body = LeaderUnavailabilityCreate(
        leader_id=leader_id, start_at=item.start_at,
        end_at=item.end_at, reason=item.reason,
    )

    with pytest.raises(HTTPException) as error:
        await router.create_unavailability(
            district_id, body, _auth(district_id), AsyncMock(),
            leaders=leaders, repo=repo,
        )
    assert error.value.status_code == 404
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_requires_planner_not_viewer(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    item = _period(leader_id)
    body = LeaderUnavailabilityCreate(
        leader_id=leader_id, start_at=item.start_at,
        end_at=item.end_at, reason=item.reason,
    )
    with pytest.raises(HTTPException) as error:
        await router.create_unavailability(
            district_id, body, _auth(district_id, Role.VIEWER), AsyncMock(),
            leaders=leaders, repo=repo,
        )
    assert error.value.status_code == 403
    leaders.get.assert_not_awaited()
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_replaces_supplied_fields_without_losing_others(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    original = repo.get.return_value
    later = original.end_at + timedelta(days=1)

    result = await router.update_unavailability(
        district_id, original.id,
        LeaderUnavailabilityUpdate(
            start_at=original.start_at + timedelta(hours=1),
            end_at=later,
            reason=UnavailabilityReason.TRAINING,
            note=None,
        ),
        _auth(district_id), AsyncMock(), leaders=leaders, repo=repo,
    )

    assert result.start_at == original.start_at
    assert result.end_at == later
    assert result.reason == UnavailabilityReason.TRAINING
    assert result.note is None
    repo.save.assert_awaited_once_with(original)


@pytest.mark.asyncio
async def test_update_only_note_preserves_dates_and_reason(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    original = repo.get.return_value
    old_start, old_end, old_reason = original.start_at, original.end_at, original.reason

    result = await router.update_unavailability(
        district_id, original.id, LeaderUnavailabilityUpdate(note="Neuer Hinweis"),
        _auth(district_id), AsyncMock(), leaders=leaders, repo=repo,
    )
    assert (result.start_at, result.end_at, result.reason) == (
        old_start, old_end, old_reason
    )
    assert result.note == "Neuer Hinweis"


@pytest.mark.asyncio
async def test_update_rejects_reversed_period(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    original = repo.get.return_value
    with pytest.raises(HTTPException) as error:
        await router.update_unavailability(
            district_id, original.id,
            LeaderUnavailabilityUpdate(end_at=original.start_at),
            _auth(district_id), AsyncMock(), leaders=leaders, repo=repo,
        )
    assert error.value.status_code == 422
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["update", "delete"])
async def test_missing_absence_is_not_mutated(
    district_id: uuid.UUID, operation: str
) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    repo.get.return_value = None
    if operation == "update":
        call = router.update_unavailability(
            district_id, uuid.uuid4(), LeaderUnavailabilityUpdate(note="X"),
            _auth(district_id), AsyncMock(), leaders=leaders, repo=repo,
        )
    else:
        call = router.delete_unavailability(
            district_id, uuid.uuid4(), _auth(district_id), AsyncMock(),
            leaders=leaders, repo=repo,
        )
    with pytest.raises(HTTPException) as error:
        await call
    assert error.value.status_code == 404
    leaders.get.assert_not_awaited()
    repo.save.assert_not_awaited()
    repo.delete.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["update", "delete"])
async def test_foreign_absence_cannot_be_mutated(
    district_id: uuid.UUID, operation: str
) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    leaders.get.return_value = SimpleNamespace(id=leader_id, district_id=uuid.uuid4())
    item = repo.get.return_value
    if operation == "update":
        call = router.update_unavailability(
            district_id, item.id, LeaderUnavailabilityUpdate(note="X"),
            _auth(district_id), AsyncMock(), leaders=leaders, repo=repo,
        )
    else:
        call = router.delete_unavailability(
            district_id, item.id, _auth(district_id), AsyncMock(),
            leaders=leaders, repo=repo,
        )
    with pytest.raises(HTTPException) as error:
        await call
    assert error.value.status_code == 404
    repo.save.assert_not_awaited()
    repo.delete.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["update", "delete"])
async def test_viewer_cannot_mutate_absence(
    district_id: uuid.UUID, operation: str
) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    item = repo.get.return_value
    if operation == "update":
        call = router.update_unavailability(
            district_id, item.id, LeaderUnavailabilityUpdate(note="X"),
            _auth(district_id, Role.VIEWER), AsyncMock(), leaders=leaders, repo=repo,
        )
    else:
        call = router.delete_unavailability(
            district_id, item.id, _auth(district_id, Role.VIEWER), AsyncMock(),
            leaders=leaders, repo=repo,
        )
    with pytest.raises(HTTPException) as error:
        await call
    assert error.value.status_code == 403
    repo.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_owned_absence(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    item = repo.get.return_value

    assert await router.delete_unavailability(
        district_id, item.id, _auth(district_id), AsyncMock(),
        leaders=leaders, repo=repo,
    ) is None
    repo.delete.assert_awaited_once_with(item.id)


@pytest.mark.asyncio
async def test_repository_failure_is_not_reported_as_success(district_id: uuid.UUID) -> None:
    leader_id = uuid.uuid4()
    leaders, repo = _repos(district_id, leader_id)
    repo.delete.side_effect = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError, match="database unavailable"):
        await router.delete_unavailability(
            district_id, repo.get.return_value.id, _auth(district_id),
            AsyncMock(), leaders=leaders, repo=repo,
        )


def test_create_schema_rejects_excessive_note() -> None:
    item = _period(uuid.uuid4())
    with pytest.raises(ValidationError):
        LeaderUnavailabilityCreate(
            leader_id=item.leader_id,
            start_at=item.start_at,
            end_at=item.end_at,
            reason=item.reason,
            note="x" * 2001,
        )
