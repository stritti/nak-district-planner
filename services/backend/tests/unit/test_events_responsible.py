from __future__ import annotations

import uuid
from datetime import date, time
from unittest.mock import AsyncMock

import pytest

from app.adapters.api.routers import events
from app.domain.models.leader import Leader, LeaderRank
from app.domain.models.planning_slot import PlanningSlot
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment


def _slot(district_id: uuid.UUID, category: str = "Gottesdienst") -> PlanningSlot:
    return PlanningSlot.create(
        district_id=district_id,
        planning_date=date(2026, 9, 26),
        planning_time=time(10),
        title="T",
        category=category,
    )


def _repos(assignments: list[ServiceAssignment], leaders: dict[uuid.UUID, Leader]):
    assignment_repo = AsyncMock()
    assignment_repo.list_by_planning_slots.return_value = assignments
    leader_repo = AsyncMock()
    leader_repo.get.side_effect = lambda lid: leaders.get(lid)
    return assignment_repo, leader_repo


@pytest.mark.asyncio
async def test_responsible_uses_leader_name_with_rank_for_any_category() -> None:
    district_id = uuid.uuid4()
    service = _slot(district_id)
    other = _slot(district_id, category="Sonstiges")
    leader = Leader.create(name="Muster", district_id=district_id, rank=LeaderRank.PRIESTER)
    assignments = [
        ServiceAssignment.create(
            event_id=service.id, planning_slot_id=service.id, leader_id=leader.id
        ),
        ServiceAssignment.create(
            event_id=other.id,
            planning_slot_id=other.id,
            leader_name="Frei Text",
            status=AssignmentStatus.CONFIRMED,
        ),
    ]
    repo, leaders = _repos(assignments, {leader.id: leader})

    result = await events._load_responsible(repo, leaders, [service, other])

    assert result[service.id].name == f"{LeaderRank.PRIESTER.value} Muster"
    assert result[service.id].leader_id == leader.id
    assert result[other.id].name == "Frei Text"
    assert result[other.id].status == AssignmentStatus.CONFIRMED


@pytest.mark.asyncio
async def test_responsible_hides_leader_of_other_district() -> None:
    slot = _slot(uuid.uuid4())
    foreign = Leader.create(name="Fremd", district_id=uuid.uuid4())
    assignment = ServiceAssignment.create(
        event_id=slot.id, planning_slot_id=slot.id, leader_id=foreign.id
    )
    repo, leaders = _repos([assignment], {foreign.id: foreign})

    result = await events._load_responsible(repo, leaders, [slot])

    assert "Fremd" not in result[slot.id].name


@pytest.mark.asyncio
async def test_responsible_empty_without_assignments() -> None:
    repo, leaders = _repos([], {})
    assert await events._load_responsible(repo, leaders, [_slot(uuid.uuid4())]) == {}
