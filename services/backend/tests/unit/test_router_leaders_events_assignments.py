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


def _auth_context(*, is_superadmin: bool = True, district_id: uuid.UUID | None = None) -> object:
    """Return a minimal auth context compatible with CurrentUserWithMemberships."""
    memberships = (
        [
            type(
                "M",
                (),
                {"scope_type": ScopeType.DISTRICT, "scope_id": district_id, "role": Role.VIEWER},
            )()
        ]
        if district_id
        else []
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
    """Create, list, update, and self-link/unlink a leader."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id)
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.leaders.assert_has_role_in_district"),
        patch("app.adapters.api.routers.leaders.SqlDistrictRepository") as district_repo_cls,
        patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls,
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = [leader]
        leader_repo.get.return_value = leader
        leader_repo.get_by_user_sub.return_value = None
        leader_repo_cls.return_value = leader_repo

        listed = await leaders_router.list_leaders(district_id, _auth_context(), db)
        created = await leaders_router.create_leader(
            district_id, LeaderCreate(name="Neu", rank=None), object(), db
        )
        updated = await leaders_router.update_leader(
            district_id, leader.id, LeaderUpdate(name="X"), object(), db
        )
        link = await leaders_router.link_self_to_leader(
            district_id,
            LeaderSelfLinkRequest(leader_id=leader.id),
            _auth_context(district_id=district_id),
            db,
        )
        unlink = await leaders_router.unlink_self_from_leader(
            district_id,
            _auth_context(district_id=district_id),
            db,
        )
        self_link = await leaders_router.get_self_link(
            district_id,
            _auth_context(district_id=district_id),
            db,
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

    with (
        patch("app.adapters.api.routers.leaders.SqlDistrictRepository") as district_repo_cls,
        patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls,
        patch(
            "app.adapters.api.routers.leaders.assert_has_role_in_district",
            side_effect=leaders_router.PermissionError("forbidden"),
        ),
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo

        leader_repo = AsyncMock()
        leader_repo.get.return_value = leader
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as create_exc:
            await leaders_router.create_leader(district_id, LeaderCreate(name="Neu"), auth, db)
        with pytest.raises(HTTPException) as update_exc:
            await leaders_router.update_leader(
                district_id,
                leader.id,
                LeaderUpdate(name="X"),
                auth,
                db,
            )
        with pytest.raises(HTTPException) as delete_exc:
            await leaders_router.delete_leader(district_id, leader.id, auth, db)

    assert create_exc.value.status_code == 403
    assert update_exc.value.status_code == 403
    assert delete_exc.value.status_code == 403


@pytest.mark.asyncio
async def test_leader_list_forbidden_without_permission() -> None:
    """Listing leaders requires VIEWER role."""
    district_id = uuid.uuid4()
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.leaders.SqlDistrictRepository") as district_repo_cls,
        patch(
            "app.adapters.api.routers.leaders.assert_has_role_in_district",
            side_effect=leaders_router.PermissionError("forbidden"),
        ),
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = District.create(name="D")
        district_repo_cls.return_value = district_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.list_leaders(district_id, _auth_context(is_superadmin=False), db)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_leader_not_found_paths() -> None:
    """List/create return 404 when district not found; update/delete when leader not found."""
    district_id = uuid.uuid4()
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.leaders.SqlDistrictRepository") as district_repo_cls,
        patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls,
    ):
        district_repo = AsyncMock()
        district_repo.get.return_value = None
        district_repo_cls.return_value = district_repo
        with pytest.raises(HTTPException):
            await leaders_router.list_leaders(district_id, _auth_context(), db)
        with pytest.raises(HTTPException):
            await leaders_router.create_leader(district_id, LeaderCreate(name="N"), object(), db)

        district_repo.get.return_value = District.create(name="D")
        leader_repo = AsyncMock()
        leader_repo.get.return_value = None
        leader_repo_cls.return_value = leader_repo
        with pytest.raises(HTTPException):
            await leaders_router.update_leader(
                district_id, uuid.uuid4(), LeaderUpdate(name="N"), object(), db
            )
        with pytest.raises(HTTPException):
            await leaders_router.delete_leader(district_id, uuid.uuid4(), object(), db)


@pytest.mark.asyncio
async def test_leader_update_wrong_district() -> None:
    """Updating a leader whose district_id does not match the URL returns 404."""
    district_id = uuid.uuid4()
    other_district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=other_district_id)
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls,
    ):
        leader_repo = AsyncMock()
        leader_repo.get.return_value = leader
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.update_leader(
                district_id,
                leader.id,
                LeaderUpdate(name="X"),
                _auth_context(),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_leader_delete_wrong_district() -> None:
    """Deleting a leader whose district_id does not match the URL returns 404."""
    district_id = uuid.uuid4()
    other_district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=other_district_id)
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls,
    ):
        leader_repo = AsyncMock()
        leader_repo.get.return_value = leader
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.delete_leader(
                district_id,
                leader.id,
                _auth_context(),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_leader_link_self_forbidden_without_district_membership() -> None:
    """Linking to a leader without VIEWER role in district returns 403."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id)
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get.return_value = leader
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.link_self_to_leader(
                district_id,
                LeaderSelfLinkRequest(leader_id=leader.id),
                _auth_context(is_superadmin=False),
                db,
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_leader_link_self_success_with_district_membership() -> None:
    """Linking to a leader with VIEWER role in district succeeds."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id)
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get.return_value = leader
        leader_repo_cls.return_value = leader_repo

        result = await leaders_router.link_self_to_leader(
            district_id,
            LeaderSelfLinkRequest(leader_id=leader.id),
            _auth_context(is_superadmin=False, district_id=district_id),
            db,
        )
    assert result.linked is True


@pytest.mark.asyncio
async def test_leader_link_self_conflict() -> None:
    """Linking to a leader that is already linked to a different user returns 409."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id, user_sub="other-user")
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get.return_value = leader
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.link_self_to_leader(
                district_id,
                LeaderSelfLinkRequest(leader_id=leader.id),
                _auth_context(district_id=district_id),
                db,
            )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_leader_link_self_leader_not_found() -> None:
    """Linking to a leader that does not exist returns 404."""
    district_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get.return_value = None
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.link_self_to_leader(
                district_id,
                LeaderSelfLinkRequest(leader_id=uuid.uuid4()),
                _auth_context(district_id=district_id),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_leader_link_self_leader_wrong_district() -> None:
    """Linking to a leader in another district returns 404."""
    district_id = uuid.uuid4()
    other_district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=other_district_id)
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get.return_value = leader
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.link_self_to_leader(
                district_id,
                LeaderSelfLinkRequest(leader_id=leader.id),
                _auth_context(district_id=district_id),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_leader_unlink_self_forbidden_without_district_membership() -> None:
    """Unlinking from a leader without VIEWER role in district returns 403."""
    district_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get_by_user_sub.return_value = None
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.unlink_self_from_leader(
                district_id,
                _auth_context(is_superadmin=False),
                db,
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_leader_unlink_self_success_with_district_membership() -> None:
    """Unlinking from a leader with VIEWER role in district succeeds."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id, user_sub="u")
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get_by_user_sub.return_value = leader
        leader_repo_cls.return_value = leader_repo

        result = await leaders_router.unlink_self_from_leader(
            district_id,
            _auth_context(is_superadmin=False, district_id=district_id),
            db,
        )
    assert result.linked is False


@pytest.mark.asyncio
async def test_leader_unlink_self_no_link() -> None:
    """Unlinking when no self-link exists returns linked=False."""
    district_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get_by_user_sub.return_value = None
        leader_repo_cls.return_value = leader_repo

        result = await leaders_router.unlink_self_from_leader(
            district_id,
            _auth_context(district_id=district_id),
            db,
        )
    assert result.linked is False
    assert result.leader is None


@pytest.mark.asyncio
async def test_leader_get_self_link_forbidden_without_district_membership() -> None:
    """Getting self-link without VIEWER role in district returns 403."""
    district_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get_by_user_sub.return_value = None
        leader_repo_cls.return_value = leader_repo

        with pytest.raises(HTTPException) as exc:
            await leaders_router.get_self_link(
                district_id,
                _auth_context(is_superadmin=False),
                db,
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_leader_get_self_link_success_with_district_membership() -> None:
    """Getting self-link with VIEWER role in district succeeds."""
    district_id = uuid.uuid4()
    leader = Leader.create(name="L", district_id=district_id, user_sub="u")
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get_by_user_sub.return_value = leader
        leader_repo_cls.return_value = leader_repo

        result = await leaders_router.get_self_link(
            district_id,
            _auth_context(is_superadmin=False, district_id=district_id),
            db,
        )
    assert result.linked is True


@pytest.mark.asyncio
async def test_leader_get_self_link_no_link() -> None:
    """Getting self-link when none exists returns linked=False."""
    district_id = uuid.uuid4()
    db = AsyncMock()

    with patch("app.adapters.api.routers.leaders.SqlLeaderRepository") as leader_repo_cls:
        leader_repo = AsyncMock()
        leader_repo.get_by_user_sub.return_value = None
        leader_repo_cls.return_value = leader_repo

        result = await leaders_router.get_self_link(
            district_id,
            _auth_context(district_id=district_id),
            db,
        )
    assert result.linked is False
    assert result.leader is None


# ===================================================================
# Service Assignment tests
# ===================================================================


@pytest.mark.asyncio
async def test_service_assignment_crud_paths() -> None:
    """Create, list, update, and delete service assignments for a PlanningSlot."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.service_assignments.assert_has_role_in_district"),
        patch(
            "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
        ) as sa_repo_cls,
    ):
        slot_repo = AsyncMock()
        slot_repo.get.return_value = slot
        slot_repo_cls.return_value = slot_repo

        sa_repo = AsyncMock()
        sa_repo.get.return_value = assignment
        sa_repo.list_by_planning_slot.return_value = [assignment]
        sa_repo_cls.return_value = sa_repo

        created = await sa_router.create_assignment(
            slot.id,
            ServiceAssignmentCreate(leader_name="Pr. Y"),
            _auth_context(),
            db,
        )
        listed = await sa_router.list_assignments(
            slot.id,
            _auth_context(),
            db,
        )
        updated = await sa_router.update_assignment(
            slot.id,
            assignment.id,
            ServiceAssignmentUpdate(status=AssignmentStatus.CONFIRMED),
            _auth_context(),
            db,
        )
        deleted = await sa_router.delete_assignment(
            slot.id,
            assignment.id,
            _auth_context(),
            db,
        )

    assert created.leader_name == "Pr. Y"
    assert len(listed) == 1
    assert updated.status == AssignmentStatus.CONFIRMED
    assert deleted is None
    assert sa_repo.delete.await_count == 1


@pytest.mark.asyncio
async def test_service_assignment_create_planning_slot_not_found() -> None:
    """Creating an assignment for a non-existent planning slot returns 404."""
    db = AsyncMock()

    with patch(
        "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
    ) as slot_repo_cls:
        slot_repo = AsyncMock()
        slot_repo.get.return_value = None
        slot_repo_cls.return_value = slot_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.create_assignment(
                uuid.uuid4(),
                ServiceAssignmentCreate(leader_name="X"),
                _auth_context(),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_service_assignment_list_planning_slot_not_found() -> None:
    """Listing assignments for a non-existent planning slot returns 404."""
    db = AsyncMock()

    with patch(
        "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
    ) as slot_repo_cls:
        slot_repo = AsyncMock()
        slot_repo.get.return_value = None
        slot_repo_cls.return_value = slot_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.list_assignments(
                uuid.uuid4(),
                _auth_context(),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_service_assignment_create_forbidden() -> None:
    """Creating assignments without PLANNER role returns 403."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()
    auth = type("A", (), {"memberships": [], "user_sub": "u", "user": None})()

    with (
        patch(
            "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.adapters.api.routers.service_assignments.assert_has_role_in_district",
            side_effect=sa_router.PermissionError("forbidden"),
        ),
    ):
        slot_repo = AsyncMock()
        slot_repo.get.return_value = slot
        slot_repo_cls.return_value = slot_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.create_assignment(
                slot.id,
                ServiceAssignmentCreate(leader_name="Pr. Y"),
                auth,
                db,
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_service_assignment_list_forbidden() -> None:
    """Listing assignments without VIEWER role returns 403."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()
    auth = type("A", (), {"memberships": [], "user_sub": "u", "user": None})()

    with (
        patch(
            "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.adapters.api.routers.service_assignments.assert_has_role_in_district",
            side_effect=sa_router.PermissionError("forbidden"),
        ),
    ):
        slot_repo = AsyncMock()
        slot_repo.get.return_value = slot
        slot_repo_cls.return_value = slot_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.list_assignments(
                slot.id,
                auth,
                db,
            )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_service_assignment_update_not_found() -> None:
    """Updating a non-existent assignment returns 404."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()

    with patch(
        "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
    ) as sa_repo_cls:
        sa_repo = AsyncMock()
        sa_repo.get.return_value = None
        sa_repo_cls.return_value = sa_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.update_assignment(
                slot.id,
                uuid.uuid4(),
                ServiceAssignmentUpdate(leader_name="X"),
                _auth_context(),
                db,
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

    with patch(
        "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
    ) as sa_repo_cls:
        sa_repo = AsyncMock()
        sa_repo.get.return_value = assignment  # event_id = slot_a.id
        sa_repo_cls.return_value = sa_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.update_assignment(
                slot_b.id,  # URL has slot_b.id
                assignment.id,
                ServiceAssignmentUpdate(leader_name="Pr. Y"),
                _auth_context(),
                db,
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

    with (
        patch(
            "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
        ) as sa_repo_cls,
    ):
        slot_repo = AsyncMock()
        slot_repo.get.return_value = None
        slot_repo_cls.return_value = slot_repo

        sa_repo = AsyncMock()
        sa_repo.get.return_value = assignment
        sa_repo_cls.return_value = sa_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.update_assignment(
                wrong_slot_id,
                assignment.id,
                ServiceAssignmentUpdate(leader_name="Pr. Y"),
                _auth_context(),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_service_assignment_delete_not_found() -> None:
    """Deleting a non-existent assignment returns 404."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()

    with patch(
        "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
    ) as sa_repo_cls:
        sa_repo = AsyncMock()
        sa_repo.get.return_value = None
        sa_repo_cls.return_value = sa_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.delete_assignment(
                slot.id,
                uuid.uuid4(),
                _auth_context(),
                db,
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

    with patch(
        "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
    ) as sa_repo_cls:
        sa_repo = AsyncMock()
        sa_repo.get.return_value = assignment
        sa_repo_cls.return_value = sa_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.delete_assignment(
                slot_b.id,
                assignment.id,
                _auth_context(),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_service_assignment_delete_planning_slot_not_found() -> None:
    """Delete fails with 404 when the planning slot is missing even if assignment exists."""
    slot = _planning_slot()
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    db = AsyncMock()

    with (
        patch(
            "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
        ) as sa_repo_cls,
    ):
        slot_repo = AsyncMock()
        slot_repo.get.return_value = None
        slot_repo_cls.return_value = slot_repo

        sa_repo = AsyncMock()
        sa_repo.get.return_value = assignment
        sa_repo_cls.return_value = sa_repo

        with pytest.raises(HTTPException) as exc:
            await sa_router.delete_assignment(
                slot.id,
                assignment.id,
                _auth_context(),
                db,
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_service_assignment_list_empty() -> None:
    """List returns an empty list when no assignments exist for a slot."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.service_assignments.assert_has_role_in_district"),
        patch(
            "app.adapters.api.routers.service_assignments.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
        ) as sa_repo_cls,
    ):
        slot_repo = AsyncMock()
        slot_repo.get.return_value = slot
        slot_repo_cls.return_value = slot_repo

        sa_repo = AsyncMock()
        sa_repo.list_by_planning_slot.return_value = []
        sa_repo_cls.return_value = sa_repo

        result = await sa_router.list_assignments(
            slot.id,
            _auth_context(),
            db,
        )

    assert result == []
