# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

import uuid
from datetime import date

import pytest

from app.domain.models.leader import Leader


@pytest.mark.parametrize(
    "active,hidden,end,target,expected",
    [
        (True, False, None, date(2030, 1, 1), True),
        (False, False, None, date(2030, 1, 1), False),
        (True, True, None, date(2030, 1, 1), False),
        (True, False, date(2026, 12, 31), date(2026, 12, 30), True),
        (True, False, date(2026, 12, 31), date(2026, 12, 31), True),
        (True, False, date(2026, 12, 31), date(2027, 1, 1), False),
    ],
)
def test_eligibility_on_local_date(active, hidden, end, target, expected):
    leader = Leader.create("Minister", uuid.uuid4(), is_active=active)
    leader.hidden_from_lists = hidden
    leader.service_end_date = end
    assert leader.is_eligible_on(target) is expected


def test_default_visibility_preserves_inactive_state():
    leader = Leader.create("Minister", uuid.uuid4(), is_active=False)
    assert leader.hidden_from_lists is False
    assert leader.service_end_date is None
    assert leader.is_active is False


from app.domain.models import leader as leader_module


@pytest.mark.parametrize("typed", ["  JÖRG   Müller ", "jörg müller", "Ｊörg Müller"])
def test_normalized_name_matches(typed):
    assert leader_module.normalize_leader_name(typed) == leader_module.normalize_leader_name(
        "Jörg Müller"
    )


def test_review_only_flags_future_invalid_assignments():
    leader = Leader.create("Minister", uuid.uuid4(), is_active=False)
    assert leader_module.assignment_needs_review(leader, date(2027, 1, 1), today=date(2026, 1, 1))
    assert not leader_module.assignment_needs_review(
        leader, date(2025, 1, 1), today=date(2026, 1, 1)
    )
    assert not leader_module.assignment_needs_review(None, date(2027, 1, 1), today=date(2026, 1, 1))


from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.adapters.api.routers import leaders as leader_router
from app.adapters.api.routers import service_assignments as assignment_router
from app.adapters.api.schemas.leader import LeaderUpdate
from tests.unit.assignment_preconditions import precondition
from tests.unit.test_router_leaders_events_assignments import _auth_context, _planning_slot


@pytest.mark.asyncio
async def test_default_leader_list_excludes_hidden_inactive():
    district = uuid.uuid4()
    active = Leader.create("Active", district)
    inactive = Leader.create("Inactive", district, is_active=False)
    hidden = Leader.create("Hidden", district)
    hidden.hidden_from_lists = True
    result = await leader_router.list_leaders(
        district,
        _auth_context(),
        AsyncMock(),
        districts=AsyncMock(get=AsyncMock(return_value=object())),
        leaders_repo=AsyncMock(list_by_district=AsyncMock(return_value=[active, inactive, hidden])),
    )
    assert [x.name for x in result] == ["Active"]


@pytest.mark.asyncio
async def test_name_only_ineligible_leader_rejected():
    slot = _planning_slot()
    leader = Leader.create("Jörg Müller", slot.district_id, is_active=False)
    with patch.object(assignment_router, "SqlLeaderRepository") as repo:
        repo.return_value.list_by_district = AsyncMock(return_value=[leader])
        repo.return_value.get = AsyncMock(return_value=leader)
        with pytest.raises(HTTPException) as error:
            await assignment_router._check_typed_name(AsyncMock(), slot, "  JÖRG   Müller ")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_planner_cannot_change_lifecycle():
    district = uuid.uuid4()
    auth = _auth_context(is_superadmin=False, district_id=district)
    auth.memberships[0].role = __import__("app.domain.models.role", fromlist=["Role"]).Role.PLANNER
    leader = Leader.create("Minister", district)
    with pytest.raises(HTTPException) as error:
        await leader_router.update_leader(
            district,
            leader.id,
            LeaderUpdate(is_active=False),
            auth,
            AsyncMock(),
            leaders_repo=AsyncMock(get=AsyncMock(return_value=leader)),
        )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_planner_may_submit_unchanged_lifecycle_fields():
    district = uuid.uuid4()
    auth = _auth_context(is_superadmin=False, district_id=district)
    auth.memberships[0].role = __import__("app.domain.models.role", fromlist=["Role"]).Role.PLANNER
    leader = Leader.create("Minister", district)
    repo = AsyncMock(get_for_update=AsyncMock(return_value=leader), save=AsyncMock())

    result = await leader_router.update_leader(
        district,
        leader.id,
        LeaderUpdate(
            name="Neuer Name",
            is_active=leader.is_active,
            hidden_from_lists=leader.hidden_from_lists,
            service_end_date=leader.service_end_date,
        ),
        auth,
        AsyncMock(),
        leaders_repo=repo,
        if_match=leader_router._leader_revision(leader),
    )

    assert result.name == "Neuer Name"
    repo.save.assert_awaited_once_with(leader)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,active,hidden,end",
    [
        ("Unknown", True, False, None),
        ("Minister", True, False, None),
        (" Minister ", False, False, None),
        ("Minister", True, True, None),
        ("Minister", True, False, date(2020, 1, 1)),
    ],
)
async def test_typed_names_eligibility(name, active, hidden, end):
    slot = _planning_slot()
    leader = Leader.create("Minister", slot.district_id, is_active=active)
    leader.hidden_from_lists = hidden
    leader.service_end_date = end
    with patch.object(assignment_router, "SqlLeaderRepository") as repo:
        repo.return_value.list_by_district = AsyncMock(return_value=[leader])
        repo.return_value.get = AsyncMock(return_value=leader)
        if name.strip() == "Minister" and not leader.is_eligible_on(slot.planning_date):
            with pytest.raises(HTTPException):
                await assignment_router._check_typed_name(AsyncMock(), slot, name)
        else:
            await assignment_router._check_typed_name(AsyncMock(), slot, name)


@pytest.mark.asyncio
async def test_stale_status_only_assignment_update_rejected():
    from app.adapters.api.schemas.service_assignment import ServiceAssignmentUpdate
    from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment

    slot = _planning_slot()
    leader = Leader.create("Minister", slot.district_id, is_active=False)
    assignment = ServiceAssignment.create(event_id=slot.id, leader_id=leader.id)
    repo = AsyncMock(get=AsyncMock(return_value=assignment))
    with (
        patch.object(assignment_router, "SqlLeaderRepository") as lr,
        patch.object(assignment_router, "SqlPlanningSlotRepository") as sr,
        patch.object(assignment_router, "ensure_leader_in_district", new=AsyncMock()),
    ):
        lr.return_value.get = AsyncMock(return_value=leader)
        sr.return_value.get = AsyncMock(return_value=slot)
        with pytest.raises(HTTPException) as error:
            await assignment_router.update_assignment(
                slot.id,
                assignment.id,
                ServiceAssignmentUpdate(status=AssignmentStatus.CONFIRMED),
                _auth_context(),
                AsyncMock(),
                slots=AsyncMock(get=AsyncMock(return_value=slot), get_for_update=AsyncMock(return_value=slot)),
                assignments_repo=repo, **precondition(slot)
            )
    assert error.value.status_code == 409
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_admin_can_restore_visibility_without_reactivating():
    district = uuid.uuid4()
    leader = Leader.create(
        "Minister",
        district,
        is_active=False,
        hidden_from_lists=True,
        service_end_date=date(2025, 1, 1),
    )
    repo = AsyncMock(get_for_update=AsyncMock(return_value=leader))
    result = await leader_router.update_leader(
        district,
        leader.id,
        LeaderUpdate(hidden_from_lists=False, service_end_date=None),
        _auth_context(),
        AsyncMock(),
        leaders_repo=repo,
        if_match=leader_router._leader_revision(leader),
    )
    assert result.hidden_from_lists is False
    assert result.is_active is False
    assert result.service_end_date is None


@pytest.mark.asyncio
async def test_admin_list_can_resolve_hidden_inactive():
    district = uuid.uuid4()
    leader = Leader.create("Minister", district, is_active=False, hidden_from_lists=True)
    result = await leader_router.list_leaders(
        district,
        _auth_context(),
        AsyncMock(),
        districts=AsyncMock(get=AsyncMock(return_value=object())),
        leaders_repo=AsyncMock(list_by_district=AsyncMock(return_value=[leader])),
        include_inactive=True,
    )
    assert result[0].id == leader.id


@pytest.mark.asyncio
async def test_viewer_cannot_request_retained_admin_list():
    district = uuid.uuid4()
    with pytest.raises(HTTPException) as error:
        await leader_router.list_leaders(
            district,
            _auth_context(is_superadmin=False, district_id=district),
            AsyncMock(),
            districts=AsyncMock(get=AsyncMock(return_value=object())),
            leaders_repo=AsyncMock(),
            include_inactive=True,
        )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_preserves_identity_and_historical_foreign_keys():
    district = uuid.uuid4()
    leader = Leader.create("Minister", district)
    repo = AsyncMock(get=AsyncMock(return_value=leader))
    await leader_router.delete_leader(
        district, leader.id, _auth_context(), AsyncMock(), leaders_repo=repo
    )
    assert not leader.is_active and leader.hidden_from_lists
    repo.delete.assert_not_called()
    repo.save.assert_awaited_once_with(leader)


@pytest.mark.asyncio
async def test_cross_district_lifecycle_write_leaves_leader_unchanged():
    leader = Leader.create("Minister", uuid.uuid4())
    repo = AsyncMock(get=AsyncMock(return_value=leader))
    with pytest.raises(HTTPException) as error:
        await leader_router.update_leader(
            uuid.uuid4(),
            leader.id,
            LeaderUpdate(service_end_date=date(2025, 1, 1)),
            _auth_context(),
            AsyncMock(),
            leaders_repo=repo,
        )
    assert error.value.status_code == 404
    assert leader.service_end_date is None
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_repository_roundtrips_lifecycle_fields():
    from app.adapters.db.orm_models.leader import LeaderORM
    from app.adapters.db.repositories.leader import SqlLeaderRepository

    leader = Leader.create(
        "Minister",
        uuid.uuid4(),
        is_active=False,
        hidden_from_lists=True,
        service_end_date=date(2026, 1, 1),
    )
    session = AsyncMock()
    row = LeaderORM()
    session.get.return_value = row
    repo = SqlLeaderRepository(session)
    await repo.save(leader)
    restored = await repo.get(leader.id)
    assert restored == leader
