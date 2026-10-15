# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Service assignments are serialized per leader and unique per planning slot (#468)."""

from __future__ import annotations

import uuid
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, call, patch

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.adapters.api.routers import service_assignments as sa_router
from app.adapters.api.schemas.service_assignment import (
    ServiceAssignmentCreate,
    ServiceAssignmentUpdate,
)
from app.adapters.db.orm_models.service_assignment import ServiceAssignmentORM
from app.domain.models.leader import Leader, LeaderRank
from app.domain.models.planning_slot import PlanningSlot
from app.domain.models.service_assignment import ServiceAssignment

_ROUTER = "app.adapters.api.routers.service_assignments."


def _slot() -> PlanningSlot:
    return PlanningSlot.create(
        district_id=uuid.uuid4(), planning_date=date(2026, 6, 15), planning_time=time(10)
    )


def _repo(value: object = None) -> AsyncMock:
    repo = AsyncMock()
    repo.get.return_value = value
    repo.get_for_update.return_value = value
    return repo


def _integrity_error(constraint_name: str) -> IntegrityError:
    """IntegrityError as SQLAlchemy raises it: the asyncpg error is the cause of ``orig``."""
    orig = Exception("integrity violation")
    cause = Exception("asyncpg error")
    cause.constraint_name = constraint_name  # type: ignore[attr-defined]
    orig.__cause__ = cause
    return IntegrityError("INSERT", {}, orig)


@pytest.mark.asyncio
async def test_rank_prefixed_typed_name_cannot_bypass_lifecycle() -> None:
    slot = _slot()
    leader = Leader.create("Max Muster", slot.district_id, rank=LeaderRank.PRIESTER)
    leader.is_active = False
    repo = AsyncMock()
    repo.list_by_district.return_value = [leader]
    repo.get.return_value = leader
    with (
        patch(_ROUTER + "SqlLeaderRepository", return_value=repo),
        patch(_ROUTER + "acquire_advisory_xact_lock", new=AsyncMock()),
        pytest.raises(HTTPException) as caught,
    ):
        await sa_router._check_typed_name(AsyncMock(), slot, "Pr. Max Muster")
    assert caught.value.status_code == 409


def _patches(order: AsyncMock, slot: PlanningSlot):
    """Allow the request, record lock + conflict check in call order."""
    leader_repo = AsyncMock()
    leader_repo.get.return_value = SimpleNamespace(is_eligible_on=lambda planning_date: True)
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    return (
        patch(_ROUTER + "require_role_in_district"),
        patch(_ROUTER + "ensure_leader_in_district", new=AsyncMock()),
        patch(_ROUTER + "acquire_advisory_xact_lock", new=order.lock),
        patch(_ROUTER + "check_service_assignment_conflicts", new=order.check),
        patch(_ROUTER + "SqlLeaderRepository", return_value=leader_repo),
        patch(_ROUTER + "SqlPlanningSlotRepository", return_value=slot_repo),
    )


@pytest.mark.asyncio
async def test_create_locks_leader_before_conflict_check() -> None:
    slot = _slot()
    leader_id = uuid.uuid4()
    order = AsyncMock()
    order.check.return_value = []
    db = AsyncMock()
    patches = _patches(order, slot)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        await sa_router.create_assignment(
            slot.id, ServiceAssignmentCreate(leader_id=leader_id), object(), db, _repo(slot), _repo()
        )

    assert order.mock_calls[:2] == [
        call.lock(db, leader_id),
        call.check(db, event_id=slot.id, leader_id=leader_id, exclude_assignment_id=None),
    ]


@pytest.mark.asyncio
async def test_update_locks_new_leader_before_conflict_check() -> None:
    slot = _slot()
    leader_id = uuid.uuid4()
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    order = AsyncMock()
    order.check.return_value = []
    db = AsyncMock()
    patches = _patches(order, slot)
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        await sa_router.update_assignment(
            slot.id, assignment.id, ServiceAssignmentUpdate(leader_id=leader_id), object(), db,
            _repo(slot), _repo(assignment), AsyncMock(),
        )

    assert order.mock_calls[0] == call.lock(db, leader_id)


@pytest.mark.asyncio
async def test_create_without_leader_takes_no_lock() -> None:
    slot = _slot()
    order = AsyncMock()
    patches = _patches(order, slot)
    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patch(_ROUTER + "_check_typed_name", new=AsyncMock()),
    ):
        await sa_router.create_assignment(
            slot.id, ServiceAssignmentCreate(leader_name="Gast"), object(), AsyncMock(),
            _repo(slot), _repo(),
        )

    order.lock.assert_not_awaited()


@pytest.mark.asyncio
async def test_second_assignment_for_slot_returns_409() -> None:
    """The unique index on planning_slot_id surfaces as 409, not 500."""
    slot = _slot()
    sa_repo = _repo()
    sa_repo.save.side_effect = _integrity_error("ix_service_assignments_planning_slot_id")
    with (
        patch(_ROUTER + "require_role_in_district"),
        patch(_ROUTER + "_check_typed_name", new=AsyncMock()),
    ):
        with pytest.raises(HTTPException) as exc:
            await sa_router.create_assignment(
                slot.id, ServiceAssignmentCreate(leader_name="Gast"), object(), AsyncMock(),
                _repo(slot), sa_repo,
            )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_other_integrity_errors_are_not_reported_as_duplicate() -> None:
    """E.g. the slot was deleted concurrently (FK violation): no misleading 409."""
    slot = _slot()
    sa_repo = _repo()
    sa_repo.save.side_effect = _integrity_error("service_assignments_planning_slot_id_fkey")
    with (
        patch(_ROUTER + "require_role_in_district"),
        patch(_ROUTER + "_check_typed_name", new=AsyncMock()),
    ):
        with pytest.raises(IntegrityError):
            await sa_router.create_assignment(
                slot.id, ServiceAssignmentCreate(leader_name="Gast"), object(), AsyncMock(),
                _repo(slot), sa_repo,
            )


def test_orm_declares_one_assignment_per_planning_slot() -> None:
    index = next(
        ix for ix in ServiceAssignmentORM.__table__.indexes if ix.name == "ix_service_assignments_planning_slot_id"
    )
    assert index.unique is True
