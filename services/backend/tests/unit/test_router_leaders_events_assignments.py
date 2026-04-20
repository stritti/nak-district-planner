from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import events as events_router
from app.adapters.api.routers import leaders as leaders_router
from app.adapters.api.routers import service_assignments as sa_router
from app.adapters.api.schemas.event import EventCreate, EventUpdate
from app.adapters.api.schemas.leader import LeaderCreate, LeaderSelfLinkRequest, LeaderUpdate
from app.adapters.api.schemas.service_assignment import (
    ServiceAssignmentCreate,
    ServiceAssignmentUpdate,
)
from app.domain.models.district import District
from app.domain.models.event import Event
from app.domain.models.leader import Leader
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment


def _auth_context(*, is_superadmin: bool = True) -> object:
    return type(
        "A",
        (),
        {
            "memberships": [],
            "user_sub": "u",
            "user": type("U", (), {"is_superadmin": is_superadmin})(),
        },
    )()


@pytest.mark.asyncio
async def test_leader_crud_and_self_link_paths() -> None:
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
            type("U", (), {"sub": "oidc|1"})(),
            db,
        )
        unlink = await leaders_router.unlink_self_from_leader(
            district_id,
            type("U", (), {"sub": "oidc|1"})(),
            db,
        )
        self_link = await leaders_router.get_self_link(
            district_id,
            type("U", (), {"sub": "oidc|1"})(),
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
async def test_event_create_list_update_paths() -> None:
    district_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    event = Event.create(
        title="Gottesdienst",
        start_at=now,
        end_at=now + timedelta(hours=1),
        district_id=district_id,
    )
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.events.assert_has_role_in_district"),
        patch("app.adapters.api.routers.events.SqlEventRepository") as repo_cls,
        patch("app.adapters.api.routers.events.SqlCongregationRepository") as cong_repo_cls,
        patch(
            "app.adapters.api.routers.events.sync_linked_invitation_event_schedule",
            new=AsyncMock(),
        ),
        patch(
            "app.adapters.api.routers.events.propagate_source_event_update",
            new=AsyncMock(),
        ),
    ):
        repo = AsyncMock()
        repo.get.return_value = event
        repo.list.return_value = ([event], 1)
        repo_cls.return_value = repo
        cong_repo = AsyncMock()
        cong_repo.list_by_ids.return_value = []
        cong_repo.get.return_value = None
        cong_repo_cls.return_value = cong_repo

        created = await events_router.create_event(
            EventCreate(
                title="Test",
                start_at=now,
                end_at=now + timedelta(hours=1),
                district_id=district_id,
            ),
            type("A", (), {"memberships": [], "user": None})(),
            db,
        )
        listed = await events_router.list_events(
            _auth_context(), db, district_id=district_id, limit=10, offset=0
        )
        updated = await events_router.update_event(
            event.id,
            EventUpdate(title="Neu", start_at=now + timedelta(days=1)),
            type("A", (), {"memberships": [], "user": None})(),
            db,
        )

    assert created.title == "Test"
    assert listed.total == 1
    assert updated.title == "Neu"


@pytest.mark.asyncio
async def test_event_update_not_found() -> None:
    with patch("app.adapters.api.routers.events.SqlEventRepository") as repo_cls:
        repo = AsyncMock()
        repo.get.return_value = None
        repo_cls.return_value = repo
        with pytest.raises(HTTPException) as exc:
            await events_router.update_event(
                uuid.uuid4(),
                EventUpdate(title="x"),
                type("A", (), {"memberships": [], "user": None})(),
                AsyncMock(),
            )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_event_list_requires_district_id_for_non_superadmin() -> None:
    with pytest.raises(HTTPException) as exc:
        await events_router.list_events(
            _auth_context(is_superadmin=False),
            AsyncMock(),
            district_id=None,
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_event_list_allows_congregation_scoped_access_with_filter() -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    event = Event.create(
        title="Gottesdienst",
        start_at=now,
        end_at=now + timedelta(hours=1),
        district_id=district_id,
        congregation_id=congregation_id,
    )

    db = AsyncMock()

    with (
        patch(
            "app.adapters.api.routers.events.assert_has_role_in_district",
            side_effect=[
                events_router.PermissionError("no district role"),
                None,
            ],
        ) as guard,
        patch("app.adapters.api.routers.events.SqlEventRepository") as repo_cls,
        patch("app.adapters.api.routers.events.SqlCongregationRepository") as cong_repo_cls,
    ):
        repo = AsyncMock()
        repo.list.return_value = ([event], 1)
        repo_cls.return_value = repo

        cong_repo = AsyncMock()
        cong_repo.get.return_value = type("C", (), {"district_id": district_id})()
        cong_repo.list_by_ids.return_value = []
        cong_repo_cls.return_value = cong_repo

        listed = await events_router.list_events(
            _auth_context(is_superadmin=False),
            db,
            district_id=district_id,
            congregation_id=congregation_id,
            limit=10,
            offset=0,
        )

    assert listed.total == 1
    assert guard.call_count == 2


@pytest.mark.asyncio
async def test_service_assignment_crud_paths() -> None:
    district_id = uuid.uuid4()
    event = Event.create(
        title="Gottesdienst",
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc) + timedelta(hours=1),
        district_id=district_id,
    )
    assignment = ServiceAssignment.create(event_id=event.id, leader_name="Pr. X")
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.service_assignments.assert_has_role_in_district"),
        patch("app.adapters.api.routers.service_assignments.SqlEventRepository") as event_repo_cls,
        patch(
            "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
        ) as sa_repo_cls,
    ):
        event_repo = AsyncMock()
        event_repo.get.return_value = event
        event_repo_cls.return_value = event_repo
        sa_repo = AsyncMock()
        sa_repo.get.return_value = assignment
        sa_repo.list_by_event.return_value = [assignment]
        sa_repo_cls.return_value = sa_repo

        created = await sa_router.create_assignment(
            event.id,
            ServiceAssignmentCreate(leader_name="Pr. Y"),
            type("A", (), {"memberships": [], "user": None})(),
            db,
        )
        listed = await sa_router.list_assignments(
            event.id,
            type("A", (), {"memberships": [], "user": None})(),
            db,
        )
        updated = await sa_router.update_assignment(
            event.id,
            assignment.id,
            ServiceAssignmentUpdate(status=AssignmentStatus.CONFIRMED),
            type("A", (), {"memberships": [], "user": None})(),
            db,
        )
        deleted = await sa_router.delete_assignment(
            event.id,
            assignment.id,
            type("A", (), {"memberships": [], "user": None})(),
            db,
        )

    assert created.leader_name == "Pr. Y"
    assert len(listed) == 1
    assert updated.status == AssignmentStatus.CONFIRMED
    assert deleted is None
    assert sa_repo.delete.await_count == 1


@pytest.mark.asyncio
async def test_service_assignment_not_found_paths() -> None:
    with (
        patch("app.adapters.api.routers.service_assignments.SqlEventRepository") as event_repo_cls,
        patch(
            "app.adapters.api.routers.service_assignments.SqlServiceAssignmentRepository"
        ) as sa_repo_cls,
    ):
        event_repo = AsyncMock()
        event_repo.get.return_value = None
        event_repo_cls.return_value = event_repo
        with pytest.raises(HTTPException):
            await sa_router.create_assignment(
                uuid.uuid4(),
                ServiceAssignmentCreate(leader_name="X"),
                type("A", (), {"memberships": [], "user": None})(),
                AsyncMock(),
            )

        sa_repo = AsyncMock()
        sa_repo.get.return_value = None
        sa_repo_cls.return_value = sa_repo
        with pytest.raises(HTTPException):
            await sa_router.update_assignment(
                uuid.uuid4(),
                uuid.uuid4(),
                ServiceAssignmentUpdate(leader_name="A"),
                type("A", (), {"memberships": [], "user": None})(),
                AsyncMock(),
            )
        with pytest.raises(HTTPException):
            await sa_router.delete_assignment(
                uuid.uuid4(),
                uuid.uuid4(),
                type("A", (), {"memberships": [], "user": None})(),
                AsyncMock(),
            )
