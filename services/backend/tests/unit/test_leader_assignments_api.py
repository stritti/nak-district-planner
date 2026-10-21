# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Assignment sub-resource of leaders: rights per congregation, home and last-assignment rules."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.routers import leaders
from app.adapters.api.schemas.leader import (
    LeaderAssignmentCreate,
    LeaderAssignmentUpdate,
    LeaderCreate,
)
from app.domain.models.leader import Leader, LeaderAssignment, SpecialRole
from app.domain.models.membership import ScopeType
from app.domain.models.role import Role

DISTRICT = uuid.uuid4()
CONG_A = uuid.uuid4()
CONG_B = uuid.uuid4()


def _auth(*memberships, superadmin=False):
    return SimpleNamespace(
        user=SimpleNamespace(is_superadmin=superadmin),
        user_sub="u-1",
        memberships=[
            SimpleNamespace(scope_type=scope, scope_id=scope_id, role=role)
            for scope, scope_id, role in memberships
        ],
    )


DISTRICT_PLANNER = _auth((ScopeType.DISTRICT, DISTRICT, Role.PLANNER))
PLANNER_A = _auth((ScopeType.CONGREGATION, CONG_A, Role.PLANNER))
VIEWER_A = _auth((ScopeType.CONGREGATION, CONG_A, Role.VIEWER))


def _leader_in_a_and_b():
    leader = Leader.create(name="Hans", district_id=DISTRICT, congregation_id=CONG_A)
    leader.assignments.append(LeaderAssignment.create(leader.id, DISTRICT, CONG_B))
    repo = AsyncMock()
    repo.get_for_update.return_value = leader
    return leader, repo


def _by_congregation(leader, congregation_id):
    return next(a for a in leader.assignments if a.congregation_id == congregation_id)


async def _add(leader, repo, auth, body):
    with patch.object(leaders, "ensure_congregation_in_district", new=AsyncMock()):
        return await leaders.add_leader_assignment(
            DISTRICT, leader.id, body, auth, AsyncMock(), leaders_repo=repo
        )


async def _patch(leader, repo, auth, assignment, body, revision="current"):
    if revision == "current":
        revision = leaders._assignment_revision(assignment)
    return await leaders.update_leader_assignment(
        DISTRICT, leader.id, assignment.id, body, auth, AsyncMock(),
        leaders_repo=repo, if_match=revision,
    )


async def _delete(leader, repo, auth, assignment, revision="current"):
    if revision == "current":
        revision = leaders._assignment_revision(assignment)
    return await leaders.remove_leader_assignment(
        DISTRICT, leader.id, assignment.id, auth, AsyncMock(),
        leaders_repo=repo, if_match=revision,
    )


# ── create validation ───────────────────────────────────────────────────────


def test_a_single_assignment_becomes_the_home_assignment():
    body = LeaderCreate(name="N", assignments=[{"congregation_id": CONG_A}])
    assert body.assignments[0].is_home is True


def test_assignments_need_exactly_one_home():
    two = [{"congregation_id": CONG_A, "is_home": True}, {"congregation_id": CONG_B, "is_home": True}]
    none = [{"congregation_id": CONG_A}, {"congregation_id": CONG_B}]
    for items in (two, none):
        with pytest.raises(ValidationError):
            LeaderCreate(name="N", assignments=items)


def test_a_congregation_can_be_assigned_only_once_and_the_list_is_not_empty():
    with pytest.raises(ValidationError):
        LeaderCreate(
            name="N",
            assignments=[
                {"congregation_id": CONG_A, "is_home": True},
                {"congregation_id": CONG_A},
            ],
        )
    with pytest.raises(ValidationError):
        LeaderCreate(name="N", assignments=[])


@pytest.mark.asyncio
async def test_create_stores_all_assignments_with_one_home():
    repo, districts = AsyncMock(), AsyncMock()
    repo.list_by_district.return_value = []
    body = LeaderCreate(
        name="Hans",
        assignments=[
            {"congregation_id": CONG_A, "role": "Gemeindevorsteher"},
            {"congregation_id": CONG_B, "is_home": True},
        ],
    )
    with (
        patch.object(leaders, "require_role_in_district"),
        patch.object(leaders, "ensure_congregation_in_district", new=AsyncMock()),
    ):
        result = await leaders.create_leader(
            DISTRICT, body, DISTRICT_PLANNER, AsyncMock(), districts=districts, leaders_repo=repo
        )
    assert [(a.congregation_id, a.is_home) for a in result.assignments] == [
        (CONG_B, True), (CONG_A, False)
    ]
    assert result.assignments[1].role == SpecialRole.GEMEINDEVORSTEHER
    saved = repo.save.await_args.args[0]
    assert {a.leader_id for a in saved.assignments} == {saved.id}


# ── rights ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_congregation_planner_changes_only_their_own_assignment():
    leader, repo = _leader_in_a_and_b()
    mine = _by_congregation(leader, CONG_A)
    changed = await _patch(
        leader, repo, PLANNER_A, mine, LeaderAssignmentUpdate(role=SpecialRole.GEMEINDEVORSTEHER)
    )
    assert changed.role == SpecialRole.GEMEINDEVORSTEHER

    foreign = _by_congregation(leader, CONG_B)
    with pytest.raises(HTTPException) as err:
        await _patch(leader, repo, PLANNER_A, foreign, LeaderAssignmentUpdate(role=None))
    assert err.value.status_code == 403
    with pytest.raises(HTTPException) as err:
        await _delete(leader, repo, PLANNER_A, foreign)
    assert err.value.status_code == 403
    assert repo.save.await_count == 1  # only the permitted change was written


@pytest.mark.asyncio
async def test_a_viewer_cannot_change_assignments():
    leader, repo = _leader_in_a_and_b()
    with pytest.raises(HTTPException) as err:
        await _patch(leader, repo, VIEWER_A, _by_congregation(leader, CONG_A), LeaderAssignmentUpdate(role=None))
    assert err.value.status_code == 403
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_only_district_planners_manage_the_district_level_assignment():
    leader, repo = _leader_in_a_and_b()
    with pytest.raises(HTTPException) as err:
        await _add(leader, repo, PLANNER_A, LeaderAssignmentCreate(congregation_id=None))
    assert err.value.status_code == 403
    added = await _add(leader, repo, DISTRICT_PLANNER, LeaderAssignmentCreate(congregation_id=None))
    assert added.congregation_id is None


@pytest.mark.asyncio
async def test_a_congregation_planner_adds_their_own_congregation_but_not_a_foreign_one():
    leader = Leader.create(name="Hans", district_id=DISTRICT, congregation_id=CONG_B)
    repo = AsyncMock()
    repo.get_for_update.return_value = leader
    with pytest.raises(HTTPException) as err:
        await _add(leader, repo, PLANNER_A, LeaderAssignmentCreate(congregation_id=uuid.uuid4()))
    assert err.value.status_code == 403
    added = await _add(leader, repo, PLANNER_A, LeaderAssignmentCreate(congregation_id=CONG_A))
    assert added.congregation_id == CONG_A and added.is_home is False


@pytest.mark.asyncio
async def test_taking_the_home_flag_needs_rights_for_the_previous_home_too():
    leader, repo = _leader_in_a_and_b()
    # PLANNER_A may edit A (the home) but the new home B belongs to another congregation.
    with pytest.raises(HTTPException) as err:
        await _patch(
            leader, repo, PLANNER_A, _by_congregation(leader, CONG_B), LeaderAssignmentUpdate(is_home=True)
        )
    assert err.value.status_code == 403
    # Moving the home away from a foreign congregation is refused as well.
    planner_b = _auth((ScopeType.CONGREGATION, CONG_B, Role.PLANNER))
    with pytest.raises(HTTPException) as err:
        await _patch(
            leader, repo, planner_b, _by_congregation(leader, CONG_B), LeaderAssignmentUpdate(is_home=True)
        )
    assert err.value.status_code == 403
    repo.save.assert_not_awaited()


# ── home flag, duplicates, removal ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_second_assignment_for_the_same_congregation_is_a_conflict():
    leader, repo = _leader_in_a_and_b()
    with pytest.raises(HTTPException) as err:
        await _add(leader, repo, DISTRICT_PLANNER, LeaderAssignmentCreate(congregation_id=CONG_A))
    assert err.value.status_code == 409 and err.value.detail["code"] == "assignment_exists"


@pytest.mark.asyncio
async def test_making_an_assignment_home_unsets_the_previous_home_atomically():
    leader, repo = _leader_in_a_and_b()
    previous_revision = leaders._assignment_revision(_by_congregation(leader, CONG_A))
    result = await _patch(
        leader, repo, DISTRICT_PLANNER, _by_congregation(leader, CONG_B), LeaderAssignmentUpdate(is_home=True)
    )
    assert result.is_home is True
    assert [a.is_home for a in (_by_congregation(leader, CONG_A), _by_congregation(leader, CONG_B))] == [False, True]
    assert leaders._assignment_revision(_by_congregation(leader, CONG_A)) != previous_revision
    assert repo.save.await_count == 1


@pytest.mark.asyncio
async def test_a_new_home_assignment_demotes_the_old_one():
    leader, repo = _leader_in_a_and_b()
    third = uuid.uuid4()
    await _add(leader, repo, DISTRICT_PLANNER, LeaderAssignmentCreate(congregation_id=third, is_home=True))
    assert [a.congregation_id for a in leader.assignments if a.is_home] == [third]


@pytest.mark.asyncio
async def test_the_home_flag_cannot_be_withdrawn_without_naming_a_new_home():
    leader, repo = _leader_in_a_and_b()
    with pytest.raises(HTTPException) as err:
        await _patch(
            leader, repo, DISTRICT_PLANNER, _by_congregation(leader, CONG_A), LeaderAssignmentUpdate(is_home=False)
        )
    assert err.value.status_code == 422


@pytest.mark.asyncio
async def test_the_role_can_be_cleared():
    leader, repo = _leader_in_a_and_b()
    mine = _by_congregation(leader, CONG_A)
    mine.role = SpecialRole.GEMEINDEVORSTEHER
    result = await _patch(leader, repo, DISTRICT_PLANNER, mine, LeaderAssignmentUpdate(role=None))
    assert result.role is None


@pytest.mark.asyncio
async def test_neither_the_home_nor_the_last_assignment_can_be_removed():
    leader, repo = _leader_in_a_and_b()
    with pytest.raises(HTTPException) as err:
        await _delete(leader, repo, DISTRICT_PLANNER, _by_congregation(leader, CONG_A))
    assert err.value.status_code == 409 and err.value.detail["code"] == "home_assignment"

    await _delete(leader, repo, DISTRICT_PLANNER, _by_congregation(leader, CONG_B))
    assert [a.congregation_id for a in leader.assignments] == [CONG_A]
    with pytest.raises(HTTPException) as err:
        await _delete(leader, repo, DISTRICT_PLANNER, leader.assignments[0])
    assert err.value.status_code == 409 and err.value.detail["code"] == "last_assignment"


# ── concurrency and lookup ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_a_missing_or_stale_revision_is_rejected_and_nothing_is_written():
    leader, repo = _leader_in_a_and_b()
    mine = _by_congregation(leader, CONG_A)
    with pytest.raises(HTTPException) as err:
        await _patch(leader, repo, DISTRICT_PLANNER, mine, LeaderAssignmentUpdate(role=None), revision=None)
    assert err.value.status_code == 428
    with pytest.raises(HTTPException) as err:
        await _patch(leader, repo, DISTRICT_PLANNER, mine, LeaderAssignmentUpdate(role=None), revision="stale")
    assert err.value.status_code == 412
    with pytest.raises(HTTPException) as err:
        await _delete(leader, repo, DISTRICT_PLANNER, _by_congregation(leader, CONG_B), revision="stale")
    assert err.value.status_code == 412
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_leader_row_is_locked_and_must_belong_to_the_district():
    leader, repo = _leader_in_a_and_b()
    await _add(leader, repo, DISTRICT_PLANNER, LeaderAssignmentCreate(congregation_id=uuid.uuid4()))
    repo.get_for_update.assert_awaited_once_with(leader.id)

    foreign = Leader.create(name="X", district_id=uuid.uuid4(), congregation_id=CONG_A)
    repo.get_for_update.return_value = foreign
    with pytest.raises(HTTPException) as err:
        await _add(foreign, repo, DISTRICT_PLANNER, LeaderAssignmentCreate(congregation_id=uuid.uuid4()))
    assert err.value.status_code == 404


@pytest.mark.asyncio
async def test_an_unknown_assignment_is_not_found():
    leader, repo = _leader_in_a_and_b()
    ghost = LeaderAssignment.create(leader.id, DISTRICT, uuid.uuid4())
    with pytest.raises(HTTPException) as err:
        await _delete(leader, repo, DISTRICT_PLANNER, ghost)
    assert err.value.status_code == 404


# ── role and level ──────────────────────────────────────────────────────────

_MISFITS = [
    {"congregation_id": None, "role": "Gemeindevorsteher"},
    {"congregation_id": CONG_A, "role": "Bezirksvorsteher"},
]


@pytest.mark.parametrize("item", _MISFITS)
def test_a_role_must_fit_the_level_of_its_assignment(item):
    with pytest.raises(ValidationError):
        LeaderAssignmentCreate(**item)
    with pytest.raises(ValidationError):
        LeaderCreate(name="N", assignments=[item])


@pytest.mark.parametrize(
    "item",
    [
        {"congregation_id": CONG_A, "role": "Gemeindevorsteher"},
        {"congregation_id": None, "role": "Bezirksvorsteher"},
        {"congregation_id": CONG_A},
        {"congregation_id": None},
    ],
)
def test_fitting_roles_and_no_role_are_accepted(item):
    assert LeaderAssignmentCreate(**item).role == item.get("role")


@pytest.mark.asyncio
async def test_changing_the_role_of_an_assignment_keeps_it_on_its_level():
    leader, repo = _leader_in_a_and_b()
    mine = _by_congregation(leader, CONG_A)
    with pytest.raises(HTTPException) as err:
        await _patch(
            leader, repo, DISTRICT_PLANNER, mine, LeaderAssignmentUpdate(role=SpecialRole.BEZIRKSVORSTEHER)
        )
    assert err.value.status_code == 422
    assert mine.role is None
    repo.save.assert_not_awaited()
