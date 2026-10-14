# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Security regressions for congregation-scoped monthly approval (#557)."""

from __future__ import annotations

import uuid
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import events
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlot
from app.domain.models.role import Role


def _auth(role: Role, scope_type: ScopeType, scope_id: uuid.UUID):
    return SimpleNamespace(
        user=SimpleNamespace(is_superadmin=False),
        user_sub="monthly-admin",
        memberships=[
            Membership.create(
                user_sub="monthly-admin",
                role=role,
                scope_type=scope_type,
                scope_id=scope_id,
            )
        ],
    )


def _request(congregation_id: uuid.UUID | None):
    return events.BulkApprovalStatusRequest(
        year=2026,
        month=11,
        congregation_id=congregation_id,
        approval_status=EventApprovalStatus.CONFIRMED,
    )


@pytest.mark.asyncio
async def test_congregation_admin_approves_only_own_slots_without_finalizing_district():
    district_id, own_id, other_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    own = PlanningSlot.create(
        district_id=district_id,
        congregation_id=own_id,
        planning_date=date(2026, 11, 3),
        planning_time=time(19, 30),
        approval_status=EventApprovalStatus.PLANNED,
    )
    foreign = PlanningSlot.create(
        district_id=district_id,
        congregation_id=other_id,
        planning_date=date(2026, 11, 3),
        planning_time=time(19, 30),
        approval_status=EventApprovalStatus.PLANNED,
    )
    district_slot = PlanningSlot.create(
        district_id=district_id,
        planning_date=date(2026, 11, 3),
        planning_time=time(19, 30),
        approval_status=EventApprovalStatus.PLANNED,
    )
    repo = AsyncMock()
    repo.list_for_date_range.return_value = [own, foreign, district_slot]
    congregations = AsyncMock()
    congregations.get.return_value = SimpleNamespace(id=own_id, district_id=district_id)
    with patch.object(events, "publish_after_commit") as published:
        response = await events.bulk_update_approval_status(
            _request(own_id), _auth(Role.CONGREGATION_ADMIN, ScopeType.CONGREGATION, own_id),
            AsyncMock(), district_id=district_id, slot_repo=repo, cong_repo=congregations,
        )
    assert response.updated_count == 1
    assert own.approval_status == EventApprovalStatus.CONFIRMED
    assert foreign.approval_status == EventApprovalStatus.PLANNED
    assert district_slot.approval_status == EventApprovalStatus.PLANNED
    repo.save.assert_awaited_once_with(own, require_existing=True)
    published.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("request_scope", ["district", "foreign"])
async def test_congregation_admin_cannot_approve_district_or_foreign_month(request_scope):
    district_id, own_id = uuid.uuid4(), uuid.uuid4()
    target = None if request_scope == "district" else uuid.uuid4()
    repo, congregations = AsyncMock(), AsyncMock()
    congregations.get.return_value = SimpleNamespace(id=target, district_id=district_id)
    with pytest.raises(HTTPException) as exc:
        await events.bulk_update_approval_status(
            _request(target), _auth(Role.CONGREGATION_ADMIN, ScopeType.CONGREGATION, own_id),
            AsyncMock(), district_id=district_id, slot_repo=repo, cong_repo=congregations,
        )
    assert exc.value.status_code == 403
    repo.list_for_date_range.assert_not_awaited()
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_forged_cross_district_congregation_id_rejected_before_slot_query():
    district_id, congregation_id = uuid.uuid4(), uuid.uuid4()
    repo, congregations = AsyncMock(), AsyncMock()
    congregations.get.return_value = SimpleNamespace(id=congregation_id, district_id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        await events.bulk_update_approval_status(
            _request(congregation_id), _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, district_id),
            AsyncMock(), district_id=district_id, slot_repo=repo, cong_repo=congregations,
        )
    assert exc.value.status_code in (400, 403, 404)
    repo.list_for_date_range.assert_not_awaited()


@pytest.mark.asyncio
async def test_district_planner_preserves_scoped_release_permission():
    district_id, congregation_id = uuid.uuid4(), uuid.uuid4()
    repo, congregations = AsyncMock(), AsyncMock()
    repo.list_for_date_range.return_value = []
    congregations.get.return_value = SimpleNamespace(id=congregation_id, district_id=district_id)
    response = await events.bulk_update_approval_status(
        _request(congregation_id), _auth(Role.PLANNER, ScopeType.DISTRICT, district_id),
        AsyncMock(), district_id=district_id, slot_repo=repo, cong_repo=congregations,
    )
    assert response.updated_count == 0


@pytest.mark.asyncio
async def test_congregation_planner_is_not_promoted_to_release_administrator():
    district_id, congregation_id = uuid.uuid4(), uuid.uuid4()
    repo, congregations = AsyncMock(), AsyncMock()
    congregations.get.return_value = SimpleNamespace(id=congregation_id, district_id=district_id)
    with pytest.raises(HTTPException) as exc:
        await events.bulk_update_approval_status(
            _request(congregation_id), _auth(Role.PLANNER, ScopeType.CONGREGATION, congregation_id),
            AsyncMock(), district_id=district_id, slot_repo=repo, cong_repo=congregations,
        )
    assert exc.value.status_code == 403
    repo.list_for_date_range.assert_not_awaited()


@pytest.mark.asyncio
async def test_max_supported_year_does_not_overflow_month_boundary():
    district_id = uuid.uuid4()
    repo = AsyncMock()
    repo.list_for_date_range.return_value = []
    request = events.BulkApprovalStatusRequest(
        year=9999, month=12, approval_status=EventApprovalStatus.CONFIRMED
    )
    response = await events.bulk_update_approval_status(
        request, _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, district_id),
        AsyncMock(), district_id=district_id, slot_repo=repo,
    )
    assert response.updated_count == 0
    assert repo.list_for_date_range.await_args.kwargs["to_date"] == date(9999, 12, 31)
