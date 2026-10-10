# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests for leaders and service-assignments routers (Event-free architecture).

Replaces the legacy Event-based tests with PlanningSlot/EventInstance patterns.
All Event CRUD tests have been removed (the events router no longer exists).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import leaders as leaders_router
from app.adapters.api.routers import service_assignments as sa_router
from app.adapters.api.schemas.leader import LeaderCreate, LeaderSelfLinkRequest, LeaderUpdate
from app.adapters.api.schemas.service_assignment import (
    ServiceAssignmentCreate,
    ServiceAssignmentUpdate,
)
from app.domain.models.district import District
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.leader import Leader
from app.domain.models.membership import ScopeType
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlot
from app.domain.models.role import Role
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment
from app.domain.planning.conflict_result import ConflictResult, Severity

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _planning_slot(**overrides: object) -> PlanningSlot:
    """Build a minimal PlanningSlot with sensible defaults."""
    return PlanningSlot.create(
        district_id=overrides.get("district_id", uuid.uuid4()),  # type: ignore[arg-type]
        planning_date=overrides.get("planning_date", date(2026, 6, 15)),  # type: ignore[arg-type]
        planning_time=overrides.get("planning_time", time(10, 0)),  # type: ignore[arg-type]
        congregation_id=overrides.get("congregation_id", uuid.uuid4()),  # type: ignore[arg-type]
        category=overrides.get("category", "Gottesdienst"),  # type: ignore[arg-type]
        title=overrides.get("title", "Gottesdienst"),  # type: ignore[arg-type]
        approval_status=overrides.get(  # type: ignore[arg-type]
            "approval_status", EventApprovalStatus.CONFIRMED
        ),
        slot_id=overrides.get("slot_id"),  # type: ignore[arg-type]
    )


def _event_instance(planning_slot_id: uuid.UUID, **overrides: object) -> EventInstance:
    """Build a minimal EventInstance linked to a PlanningSlot."""
    return EventInstance.create(
        planning_slot_id=planning_slot_id,
        title=overrides.get("title", "Gottesdienst"),  # type: ignore[arg-type]
        actual_start_at=overrides.get(  # type: ignore[arg-type]
            "actual_start_at", datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
        ),
        actual_end_at=overrides.get(  # type: ignore[arg-type]
            "actual_end_at", datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
        ),
        source=overrides.get("source", EventSource.INTERNAL),  # type: ignore[arg-type]
        visibility=overrides.get("visibility", EventVisibility.PUBLIC),  # type: ignore[arg-type]
    )


def _auth_context(
    *,
    is_superadmin: bool = True,
    district_id: uuid.UUID | None = None,
    congregation_id: uuid.UUID | None = None,
) -> object:
    """Return a minimal auth context compatible with CurrentUserWithMemberships."""
    memberships: list[object] = []
    if district_id:
        memberships.append(
            type(
                "M",
                (),
                {"scope_type": ScopeType.DISTRICT, "scope_id": district_id, "role": Role.VIEWER},
            )()
        )
    if congregation_id:
        memberships.append(
            type(
                "M",
                (),
                {
                    "scope_type": ScopeType.CONGREGATION,
                    "scope_id": congregation_id,
                    "role": Role.VIEWER,
                },
            )()
        )
    return type(
        "A",
        (),
        {
            "memberships": memberships,
            "user_sub": "u",
            "user": type("U", (), {"is_superadmin": is_superadmin})(),
        },
    )()


# ===================================================================
# Leader tests
# ===================================================================


@pytest.mark.asyncio
async def test_leader_crud_and_self_link_paths() -> None:
    """List, create, update, link-self, unlink-self, and get-self-link happy paths."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id)
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    leader_repo = AsyncMock()
    leader_repo.list_by_district.return_value = [leader]
    leader_repo.get.return_value = leader
    leader_repo.get_by_user_sub.return_value = None
    with patch("app.adapters.api.routers.leaders.require_role_in_district"):
        listed = await leaders_router.list_leaders(
            district_id, _auth_context(), db, districts=district_repo, leaders_repo=leader_repo
        )
        created = await leaders_router.create_leader(
            district_id, LeaderCreate(name="Neu", rank=None), object(), db,
            districts=district_repo, leaders_repo=leader_repo,
        )
        updated = await leaders_router.update_leader(
            district_id, leader.id, LeaderUpdate(name="X"), object(), db, leaders_repo=leader_repo
        )
        link = await leaders_router.link_self_to_leader(
            district_id,
            LeaderSelfLinkRequest(leader_id=leader.id),
            _auth_context(district_id=district_id),
            db,
            leaders_repo=leader_repo,
        )
        unlink = await leaders_router.unlink_self_from_leader(
            district_id,
            _auth_context(district_id=district_id),
            db,
            leaders_repo=leader_repo,
        )
        self_link = await leaders_router.get_self_link(
            district_id,
            _auth_context(district_id=district_id),
            db,
            leaders_repo=leader_repo,
        )

    assert listed
    assert created.name == "Neu"
    assert updated.name == "X"
    assert link.linked is True
    assert unlink.linked is False
    assert self_link is not None

@pytest.mark.asyncio
async def test_leader_crud_forbidden_without_permission() -> None:
    """Creating, updating, and deleting leaders require PLANNER role."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id)
    db = AsyncMock()
    auth = type("A", (), {"memberships": [], "user_sub": "u", "user": None})()
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    leader_repo = AsyncMock()
    leader_repo.get.return_value = leader
    with patch(
        "app.adapters.api.routers.leaders.require_role_in_district",
        side_effect=HTTPException(status_code=403, detail="forbidden"),
    ):
        with pytest.raises(HTTPException) as create_exc:
            await leaders_router.create_leader(
                district_id, LeaderCreate(name="N"), auth, db, districts=district_repo, leaders_repo=leader_repo
            )
        with pytest.raises(HTTPException) as update_exc:
            await leaders_router.update_leader(
                district_id, leader.id, LeaderUpdate(name="X"), auth, db, leaders_repo=leader_repo
            )
        with pytest.raises(HTTPException) as delete_exc:
            await leaders_router.delete_leader(district_id, leader.id, auth, db, leaders_repo=leader_repo)

    assert create_exc.value.status_code == 403
    assert update_exc.value.status_code == 403
    assert delete_exc.value.status_code == 403

@pytest.mark.asyncio
async def test_leader_list_forbidden_without_permission() -> None:
    """Listing leaders requires VIEWER role."""
    district_id = uuid.uuid4()
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = District.create(name="D")
    with patch(
        "app.adapters.api.routers.leaders.require_role_in_district",
        side_effect=HTTPException(status_code=403, detail="forbidden"),
    ):
        with pytest.raises(HTTPException) as exc:
            await leaders_router.list_leaders(
                district_id, _auth_context(is_superadmin=False), db, districts=district_repo, leaders_repo=AsyncMock()
            )

    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_leader_not_found_paths() -> None:
    """List/create return 404 when district not found; update/delete when leader not found."""
    district_id = uuid.uuid4()
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = None
    with pytest.raises(HTTPException):
        await leaders_router.list_leaders(
            district_id, _auth_context(), db, districts=district_repo, leaders_repo=AsyncMock()
        )
    with pytest.raises(HTTPException):
        await leaders_router.create_leader(
            district_id, LeaderCreate(name="N"), _auth_context(), db, districts=district_repo, leaders_repo=AsyncMock()
        )
    district_repo.get.return_value = District.create(name="D")
    leader_repo = AsyncMock()
    leader_repo.get.return_value = None
    with pytest.raises(HTTPException):
        await leaders_router.update_leader(
            district_id, uuid.uuid4(), LeaderUpdate(name="N"), _auth_context(), db, leader_repo
        )
    with pytest.raises(HTTPException):
        await leaders_router.delete_leader(district_id, uuid.uuid4(), _auth_context(), db, leaders_repo=leader_repo)

@pytest.mark.asyncio
async def test_leader_update_wrong_district() -> None:
    """Updating a leader whose district_id does not match the URL returns 404."""
    district_id = uuid.uuid4()
    other_district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=other_district_id)
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get.return_value = leader
    with pytest.raises(HTTPException) as exc:
        await leaders_router.update_leader(
            district_id, leader.id, LeaderUpdate(name="X"), _auth_context(), db, leader_repo
        )

    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_leader_delete_wrong_district() -> None:
    """Deleting a leader whose district_id does not match the URL returns 404."""
    district_id = uuid.uuid4()
    other_district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=other_district_id)
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get.return_value = leader
    with pytest.raises(HTTPException) as exc:
        await leaders_router.delete_leader(
            district_id, leader.id, _auth_context(), db, leaders_repo=leader_repo
        )

    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_leader_link_self_forbidden_without_district_membership() -> None:
    """Linking to a leader without VIEWER role in district returns 403."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id)
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get.return_value = leader
    with pytest.raises(HTTPException) as exc:
        await leaders_router.link_self_to_leader(
            district_id,
            LeaderSelfLinkRequest(leader_id=leader.id),
            _auth_context(is_superadmin=False),
            db,
            leaders_repo=leader_repo,
        )

    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_leader_link_self_success_with_district_membership() -> None:
    """Linking to a leader with VIEWER role in district succeeds."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id)
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get.return_value = leader
    result = await leaders_router.link_self_to_leader(
        district_id,
        LeaderSelfLinkRequest(leader_id=leader.id),
        _auth_context(is_superadmin=False, district_id=district_id),
        db,
        leaders_repo=leader_repo,
    )

    assert result.linked is True

@pytest.mark.asyncio
async def test_leader_link_self_success_with_congregation_membership() -> None:
    """Linking to a leader with VIEWER role only in the leader's congregation succeeds.

    Regression test: a user with a CONGREGATION-scoped membership (a supported
    approval path, see registrations.py) must not be rejected just because
    they lack a DISTRICT-scoped membership.
    """
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id, congregation_id=congregation_id)
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get.return_value = leader
    result = await leaders_router.link_self_to_leader(
        district_id,
        LeaderSelfLinkRequest(leader_id=leader.id),
        _auth_context(is_superadmin=False, congregation_id=congregation_id),
        db,
        leaders_repo=leader_repo,
    )

    assert result.linked is True

@pytest.mark.asyncio
async def test_leader_link_self_conflict() -> None:
    """Linking to a leader that is already linked to a different user returns 409."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id, user_sub="other-user")
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get.return_value = leader
    with pytest.raises(HTTPException) as exc:
        await leaders_router.link_self_to_leader(
            district_id,
            LeaderSelfLinkRequest(leader_id=leader.id),
            _auth_context(district_id=district_id),
            db,
            leaders_repo=leader_repo,
        )

    assert exc.value.status_code == 409

@pytest.mark.asyncio
async def test_leader_link_self_leader_not_found() -> None:
    """Linking to a leader that does not exist returns 404."""
    district_id = uuid.uuid4()
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await leaders_router.link_self_to_leader(
            district_id,
            LeaderSelfLinkRequest(leader_id=uuid.uuid4()),
            _auth_context(district_id=district_id),
            db,
            leaders_repo=leader_repo,
        )

    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_leader_link_self_leader_wrong_district() -> None:
    """Linking to a leader in another district returns 404."""
    district_id = uuid.uuid4()
    other_district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=other_district_id)
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get.return_value = leader
    with pytest.raises(HTTPException) as exc:
        await leaders_router.link_self_to_leader(
            district_id,
            LeaderSelfLinkRequest(leader_id=leader.id),
            _auth_context(district_id=district_id),
            db,
            leaders_repo=leader_repo,
        )

    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_leader_unlink_self_forbidden_without_district_membership() -> None:
    """Unlinking from a leader without VIEWER role in district returns 403."""
    district_id = uuid.uuid4()
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get_by_user_sub.return_value = None
    with pytest.raises(HTTPException) as exc:
        await leaders_router.unlink_self_from_leader(
            district_id,
            _auth_context(is_superadmin=False),
            db,
            leaders_repo=leader_repo,
        )

    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_leader_unlink_self_success_with_district_membership() -> None:
    """Unlinking from a leader with VIEWER role in district succeeds."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id, user_sub="u")
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get_by_user_sub.return_value = leader
    result = await leaders_router.unlink_self_from_leader(
        district_id,
        _auth_context(is_superadmin=False, district_id=district_id),
        db,
        leaders_repo=leader_repo,
    )

    assert result.linked is False

@pytest.mark.asyncio
async def test_leader_unlink_self_success_with_congregation_membership() -> None:
    """Unlinking with VIEWER role only in the linked leader's congregation succeeds."""
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    leader = Leader.create(
        name="L", district_id=district_id, congregation_id=congregation_id, user_sub="u"
    )
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get_by_user_sub.return_value = leader
    result = await leaders_router.unlink_self_from_leader(
        district_id,
        _auth_context(is_superadmin=False, congregation_id=congregation_id),
        db,
        leaders_repo=leader_repo,
    )

    assert result.linked is False

@pytest.mark.asyncio
async def test_leader_unlink_self_no_link() -> None:
    """Unlinking when no self-link exists returns linked=False."""
    district_id = uuid.uuid4()
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get_by_user_sub.return_value = None
    result = await leaders_router.unlink_self_from_leader(
        district_id,
        _auth_context(district_id=district_id),
        db,
        leaders_repo=leader_repo,
    )

    assert result.linked is False
    assert result.leader is None

@pytest.mark.asyncio
async def test_leader_get_self_link_forbidden_without_district_membership() -> None:
    """Getting self-link without VIEWER role in district returns 403."""
    district_id = uuid.uuid4()
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get_by_user_sub.return_value = None
    with pytest.raises(HTTPException) as exc:
        await leaders_router.get_self_link(
            district_id,
            _auth_context(is_superadmin=False),
            db,
            leaders_repo=leader_repo,
        )

    assert exc.value.status_code == 403

@pytest.mark.asyncio
async def test_leader_get_self_link_success_with_district_membership() -> None:
    """Getting self-link with VIEWER role in district succeeds."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id, user_sub="u")
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get_by_user_sub.return_value = leader
    result = await leaders_router.get_self_link(
        district_id,
        _auth_context(district_id=district_id),
        db,
        leaders_repo=leader_repo,
    )

    assert result.linked is True

@pytest.mark.asyncio
async def test_leader_get_self_link_success_with_congregation_membership() -> None:
    """Getting self-link with VIEWER role only in the leader's congregation succeeds."""
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    leader = Leader.create(
        name="L", district_id=district_id, congregation_id=congregation_id, user_sub="u"
    )
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get_by_user_sub.return_value = leader
    result = await leaders_router.get_self_link(
        district_id,
        _auth_context(is_superadmin=False, congregation_id=congregation_id),
        db,
        leaders_repo=leader_repo,
    )

    assert result.linked is True

@pytest.mark.asyncio
async def test_leader_get_self_link_no_link() -> None:
    """Getting self-link when none exists returns linked=False."""
    district_id = uuid.uuid4()
    db = AsyncMock()
    leader_repo = AsyncMock()
    leader_repo.get_by_user_sub.return_value = None
    result = await leaders_router.get_self_link(
        district_id,
        _auth_context(district_id=district_id),
        db,
        leaders_repo=leader_repo,
    )

    assert result.linked is False
    assert result.leader is None

@pytest.mark.asyncio
async def test_service_assignment_crud_paths() -> None:
    """Create, list, update, and delete service assignments for a PlanningSlot."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    db = AsyncMock()

    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    sa_repo = AsyncMock()
    sa_repo.get.return_value = assignment
    sa_repo.list_by_planning_slot.return_value = [assignment]
    with patch("app.adapters.api.routers.service_assignments.require_role_in_district"):
        created = await sa_router.create_assignment(
            slot.id,
            ServiceAssignmentCreate(leader_name="Pr. Y"),
            _auth_context(),
            db,
            slot_repo,
            sa_repo,
        )
        listed = await sa_router.list_assignments(
            slot.id,
            _auth_context(),
            db,
            slot_repo,
            sa_repo,
        )
        updated = await sa_router.update_assignment(
            slot.id,
            assignment.id,
            ServiceAssignmentUpdate(status=AssignmentStatus.CONFIRMED),
            _auth_context(),
            db,
            slot_repo,
            sa_repo,
        )
        deleted = await sa_router.delete_assignment(
            slot.id,
            assignment.id,
            _auth_context(),
            db,
            slot_repo,
            sa_repo,
        )
    assert created.leader_name == "Pr. Y"
    assert len(listed) == 1
    assert updated.status == AssignmentStatus.CONFIRMED
    assert deleted is None
    assert sa_repo.delete.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["create", "update", "delete"])
async def test_service_assignment_writes_touch_planning_slot(action: str) -> None:
    """Assignment changes bump the slot revision so ICS feeds re-sync (#466)."""
    slot = _planning_slot(district_id=uuid.uuid4())
    before = datetime(2026, 1, 1, tzinfo=UTC)
    slot.updated_at = before
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    sa_repo = AsyncMock()
    sa_repo.get.return_value = assignment
    args = (_auth_context(), AsyncMock(), slot_repo, sa_repo)
    with patch("app.adapters.api.routers.service_assignments.require_role_in_district"):
        if action == "create":
            await sa_router.create_assignment(
                slot.id, ServiceAssignmentCreate(leader_name="Pr. Y"), *args
            )
        elif action == "update":
            await sa_router.update_assignment(
                slot.id, assignment.id, ServiceAssignmentUpdate(leader_name="Pr. Z"), *args
            )
        else:
            await sa_router.delete_assignment(slot.id, assignment.id, *args)

    assert slot.updated_at > before
    slot_repo.save.assert_awaited_once_with(slot)


@pytest.mark.asyncio
async def test_service_assignment_create_blocks_conflict() -> None:
    slot = _planning_slot()
    db = AsyncMock()
    db.scalar.return_value = slot.district_id  # leader belongs to the district
    leader_id = uuid.uuid4()
    slot_repo = AsyncMock()
    slot_repo.get = AsyncMock(return_value=slot)
    sa_repo = AsyncMock()
    sa_repo.save = AsyncMock()
    with (
        patch("app.adapters.api.routers.service_assignments.require_role_in_district"),
        patch(
            "app.adapters.api.routers.service_assignments.check_service_assignment_conflicts",
            new=AsyncMock(
                return_value=[ConflictResult("no_double_booking", Severity.BLOCK, "Konflikt")]
            ),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            await sa_router.create_assignment(
                slot.id,
                ServiceAssignmentCreate(leader_id=leader_id),
                _auth_context(),
                db,
                slot_repo,
                sa_repo,
            )

    assert exc.value.status_code == 409
    sa_repo.save.assert_not_awaited()

@pytest.mark.asyncio
async def test_service_assignment_create_allows_confirmed_warning() -> None:
    slot = _planning_slot()
    db = AsyncMock()
    db.scalar.return_value = slot.district_id  # leader belongs to the district
    leader_id = uuid.uuid4()
    slot_repo = AsyncMock()
    slot_repo.get = AsyncMock(return_value=slot)
    sa_repo = AsyncMock()
    sa_repo.save = AsyncMock()
    with (
        patch("app.adapters.api.routers.service_assignments.require_role_in_district"),
        patch(
            "app.adapters.api.routers.service_assignments.check_service_assignment_conflicts",
            new=AsyncMock(
                return_value=[ConflictResult("travel_time_check", Severity.WARN, "Hinweis")]
            ),
        ),
    ):
        result = await sa_router.create_assignment(
            slot.id,
            ServiceAssignmentCreate(leader_id=leader_id, confirm_warnings=True),
            _auth_context(),
            db,
            slot_repo,
            sa_repo,
        )

    assert result.leader_id == leader_id
    sa_repo.save.assert_awaited_once()
@pytest.mark.asyncio
async def test_service_assignment_create_planning_slot_not_found() -> None:
    """Creating an assignment for a non-existent planning slot returns 404."""
    db = AsyncMock()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await sa_router.create_assignment(
            uuid.uuid4(),
            ServiceAssignmentCreate(leader_name="X"),
            _auth_context(),
            db,
            slot_repo,
            AsyncMock(),
        )

    assert exc.value.status_code == 404
@pytest.mark.asyncio
async def test_service_assignment_list_planning_slot_not_found() -> None:
    """Listing assignments for a non-existent planning slot returns 404."""
    db = AsyncMock()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await sa_router.list_assignments(
            uuid.uuid4(),
            _auth_context(),
            db,
            slot_repo,
            AsyncMock(),
        )

    assert exc.value.status_code == 404
@pytest.mark.asyncio
async def test_service_assignment_create_forbidden() -> None:
    """Creating assignments without PLANNER role returns 403."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()
    auth = type("A", (), {"memberships": [], "user_sub": "u", "user": None})()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    with patch(
        "app.adapters.api.routers.service_assignments.require_role_in_district",
        side_effect=HTTPException(status_code=403, detail="forbidden"),
    ):
        with pytest.raises(HTTPException) as exc:
            await sa_router.create_assignment(
                slot.id,
                ServiceAssignmentCreate(leader_name="Pr. Y"),
                auth,
                db,
                slot_repo,
                AsyncMock(),
            )

    assert exc.value.status_code == 403
@pytest.mark.asyncio
async def test_service_assignment_list_forbidden() -> None:
    """Listing assignments without VIEWER role returns 403."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()
    auth = type("A", (), {"memberships": [], "user_sub": "u", "user": None})()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    with patch(
        "app.adapters.api.routers.service_assignments.require_role_in_district",
        side_effect=HTTPException(status_code=403, detail="forbidden"),
    ):
        with pytest.raises(HTTPException) as exc:
            await sa_router.list_assignments(
                slot.id,
                auth,
                db,
                slot_repo,
                AsyncMock(),
            )

    assert exc.value.status_code == 403
@pytest.mark.asyncio
async def test_service_assignment_update_not_found() -> None:
    """Updating a non-existent assignment returns 404."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()
    sa_repo = AsyncMock()
    sa_repo.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await sa_router.update_assignment(
            slot.id,
            uuid.uuid4(),
            ServiceAssignmentUpdate(leader_name="X"),
            _auth_context(),
            db,
            AsyncMock(),
            sa_repo,
        )

    assert exc.value.status_code == 404
@pytest.mark.asyncio
async def test_service_assignment_update_event_id_mismatch() -> None:
    """Updating with an assignment whose event_id differs from the URL returns 404."""
    district_id = uuid.uuid4()
    slot_a = _planning_slot(district_id=district_id)
    slot_b = _planning_slot(district_id=district_id)
    assignment = ServiceAssignment.create(event_id=slot_a.id, leader_name="Pr. X")
    db = AsyncMock()
    sa_repo = AsyncMock()
    sa_repo.get.return_value = assignment  # event_id = slot_a.id
    with pytest.raises(HTTPException) as exc:
        await sa_router.update_assignment(
            slot_b.id,  # URL has slot_b.id
            assignment.id,
            ServiceAssignmentUpdate(leader_name="Pr. Y"),
            _auth_context(),
            db,
            AsyncMock(),
            sa_repo,
        )

    assert exc.value.status_code == 404
@pytest.mark.asyncio
async def test_service_assignment_update_planning_slot_not_found() -> None:
    """Updating fails when the planning slot lookup returns None."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    wrong_slot_id = uuid.uuid4()
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    db = AsyncMock()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = None
    sa_repo = AsyncMock()
    sa_repo.get.return_value = assignment
    with pytest.raises(HTTPException) as exc:
        await sa_router.update_assignment(
            wrong_slot_id,
            assignment.id,
            ServiceAssignmentUpdate(leader_name="Pr. Y"),
            _auth_context(),
            db,
            slot_repo,
            sa_repo,
        )

    assert exc.value.status_code == 404
@pytest.mark.asyncio
async def test_service_assignment_delete_not_found() -> None:
    """Deleting a non-existent assignment returns 404."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()
    sa_repo = AsyncMock()
    sa_repo.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await sa_router.delete_assignment(
            slot.id,
            uuid.uuid4(),
            _auth_context(),
            db,
            AsyncMock(),
            sa_repo,
        )

    assert exc.value.status_code == 404
@pytest.mark.asyncio
async def test_service_assignment_delete_event_id_mismatch() -> None:
    """Deleting with an assignment whose event_id differs from the URL returns 404."""
    district_id = uuid.uuid4()
    slot_a = _planning_slot(district_id=district_id)
    slot_b = _planning_slot(district_id=district_id)
    assignment = ServiceAssignment.create(event_id=slot_a.id, leader_name="Pr. X")
    db = AsyncMock()
    sa_repo = AsyncMock()
    sa_repo.get.return_value = assignment
    with pytest.raises(HTTPException) as exc:
        await sa_router.delete_assignment(
            slot_b.id,
            assignment.id,
            _auth_context(),
            db,
            AsyncMock(),
            sa_repo,
        )

    assert exc.value.status_code == 404
@pytest.mark.asyncio
async def test_service_assignment_delete_planning_slot_not_found() -> None:
    """Delete fails with 404 when the planning slot is missing even if assignment exists."""
    slot = _planning_slot()
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    db = AsyncMock()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = None
    sa_repo = AsyncMock()
    sa_repo.get.return_value = assignment
    with pytest.raises(HTTPException) as exc:
        await sa_router.delete_assignment(
            slot.id,
            assignment.id,
            _auth_context(),
            db,
            slot_repo,
            sa_repo,
        )

    assert exc.value.status_code == 404
@pytest.mark.asyncio
async def test_service_assignment_list_empty() -> None:
    """List returns an empty list when no assignments exist for a slot."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    sa_repo = AsyncMock()
    sa_repo.list_by_planning_slot.return_value = []
    with patch("app.adapters.api.routers.service_assignments.require_role_in_district"):
        result = await sa_router.list_assignments(
            slot.id,
            _auth_context(),
            db,
            slot_repo,
            sa_repo,
        )

    assert result == []


@pytest.mark.asyncio
async def test_leader_routes_check_role_before_loading_foreign_rows() -> None:
    """Outsiders get 403 (audited as ACCESS_DENIED), not 404 from an RLS-hidden row."""
    district_id = uuid.uuid4()
    outsider = _auth_context(is_superadmin=False)
    db = AsyncMock()
    district_repo = AsyncMock()
    district_repo.get.return_value = None
    leader_repo = AsyncMock()
    leader_repo.get.return_value = None

    calls = [
        leaders_router.list_leaders(
            district_id, outsider, db, districts=district_repo, leaders_repo=leader_repo
        ),
        leaders_router.create_leader(
            district_id, LeaderCreate(name="N"), outsider, db,
            districts=district_repo, leaders_repo=leader_repo,
        ),
        leaders_router.update_leader(
            district_id, uuid.uuid4(), LeaderUpdate(name="X"), outsider, db, leader_repo
        ),
        leaders_router.delete_leader(
            district_id, uuid.uuid4(), outsider, db, leaders_repo=leader_repo
        ),
    ]
    for call in calls:
        with pytest.raises(HTTPException) as exc:
            await call
        assert exc.value.status_code == 403

    district_repo.get.assert_not_awaited()
    leader_repo.get.assert_not_awaited()
    leader_repo.delete.assert_not_awaited()
