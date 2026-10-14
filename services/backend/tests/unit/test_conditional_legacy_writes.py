# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""All writers of versioned event and leader records honor strong revisions."""

import uuid
from datetime import date, time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import events, leaders
from app.adapters.api.schemas.leader import LeaderUpdate
from app.domain.models.leader import Leader
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus


def _slot() -> PlanningSlot:
    return PlanningSlot.create(
        district_id=uuid.uuid4(),
        planning_date=date(2026, 10, 14),
        planning_time=time(10),
        title="Gottesdienst",
    )


@pytest.mark.asyncio
async def test_legacy_event_requires_revision_and_rejects_stale_writes():
    slot = _slot()
    slots, instances = AsyncMock(), AsyncMock()
    slots.get.return_value = slot
    slots.get_for_update.return_value = slot
    instances.get_by_planning_slot.return_value = None
    with patch.object(events, "require_role_in_district"):
        for revision, expected_status in [(None, 428), ('"stale"', 412)]:
            with pytest.raises(HTTPException) as error:
                await events.update_event(
                    slot.id, events.EventUpdate(title="Overwrite"), object(),
                    AsyncMock(), slot_repo=slots, inst_repo=instances, if_match=revision,
                )
            assert error.value.status_code == expected_status
    slots.save.assert_not_awaited()
    assert slot.title == "Gottesdienst"


@pytest.mark.asyncio
async def test_legacy_leader_requires_revision_and_rejects_stale_writes():
    leader = Leader.create(name="Previous", district_id=uuid.uuid4())
    repo = AsyncMock()
    repo.get.return_value = leader
    repo.get_for_update.return_value = leader
    with patch.object(leaders, "require_role_in_district"):
        for revision, expected_status in [(None, 428), ('"stale"', 412)]:
            with pytest.raises(HTTPException) as error:
                await leaders.update_leader(
                    leader.district_id, leader.id, LeaderUpdate(name="Overwrite"),
                    object(), AsyncMock(), leaders_repo=repo, if_match=revision,
                )
            assert error.value.status_code == expected_status
    repo.save.assert_not_awaited()
    assert leader.name == "Previous"


@pytest.mark.asyncio
async def test_event_snapshot_without_instance_is_internal_and_versioned():
    slot = _slot()
    slots, instances = AsyncMock(), AsyncMock()
    slots.get.return_value = slot
    instances.get_by_planning_slot.return_value = None
    with (
        patch.object(events, "require_role_in_district"),
        patch.object(events, "_load_responsible", AsyncMock(return_value={})),
    ):
        response = await events.get_event(
            slot.id, object(), slot_repo=slots, inst_repo=instances,
            assignments_repo=AsyncMock(), leaders_repo=AsyncMock(),
        )
    assert response.source.value == "INTERNAL"
    assert response.revision == events._slot_revision(slot)


@pytest.mark.asyncio
async def test_event_snapshot_hides_other_tenants():
    slots = AsyncMock()
    slots.get.return_value = _slot()
    with (
        patch.object(events, "require_role_in_district", side_effect=HTTPException(403)),
        pytest.raises(HTTPException) as error,
    ):
        await events.get_event(uuid.uuid4(), object(), slot_repo=slots)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_cancelled_event_cannot_be_changed_using_inline_path():
    slot = _slot()
    slot.status = PlanningSlotStatus.CANCELLED
    slots = AsyncMock()
    slots.get_for_update.return_value = slot
    with (
        patch.object(events, "require_role_in_district"),
        pytest.raises(HTTPException) as error,
    ):
        await events.inline_update_event(
            slot.id,
            events.EventInlineUpdate(title="Versteckte Änderung"),
            object(),
            AsyncMock(),
            if_match=events._slot_revision(slot),
            slot_repo=slots,
        )
    assert error.value.status_code == 409
    slots.save.assert_not_awaited()
    assert slot.title == "Gottesdienst"
