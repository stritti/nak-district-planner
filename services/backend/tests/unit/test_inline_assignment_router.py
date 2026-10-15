# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Conditional inline minister assignment contract and edge cases."""

import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.revisions import slot_revision
from app.adapters.api.routers import service_assignments
from app.adapters.api.schemas.service_assignment import InlineAssignmentChange
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.role import Role
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment


def _slot() -> PlanningSlot:
    return PlanningSlot.create(
        district_id=uuid.uuid4(),
        planning_date=date(2026, 10, 14),
        planning_time=time(10),
        title="Gottesdienst",
    )


async def _call(slot: PlanningSlot, *, revision: str | None, existing=None, permitted=True, conflict=False):
    slots, assignments, instances = AsyncMock(), AsyncMock(), AsyncMock()
    instances.get_by_planning_slot.return_value = None
    slots.get.return_value = slot
    slots.get_for_update.return_value = slot
    assignments.list_by_planning_slot.return_value = existing or []
    leader_id = uuid.uuid4()
    with (
        patch.object(service_assignments, "require_role_in_district") as authorize,
        patch.object(service_assignments, "_check_leader", new_callable=AsyncMock) as check,
    ):
        if not permitted:
            authorize.side_effect = HTTPException(status_code=403, detail="Not allowed")
        if conflict:
            check.side_effect = HTTPException(status_code=409, detail="Assignment conflict")
        try:
            result = await service_assignments.inline_change_assignment(
                slot.id,
                InlineAssignmentChange(leader_id=leader_id),
                object(),
                AsyncMock(),
                if_match=revision,
                slots=slots,
                assignments_repo=assignments,
                instance_repo=instances,
            )
        except HTTPException:
            if revision is None:
                slots.get.assert_not_awaited()
                slots.get_for_update.assert_not_awaited()
                instances.get_by_planning_slot.assert_not_awaited()
                assignments.list_by_planning_slot.assert_not_awaited()
                authorize.assert_not_called()
            assignments.save.assert_not_awaited()
            slots.save.assert_not_awaited()
            raise
    authorize.assert_called_once_with(authorize.call_args.args[0], Role.PLANNER, slot.district_id)
    check.assert_awaited_once()
    return result, assignments, slots, leader_id


@pytest.mark.asyncio
async def test_inline_create_requires_exact_revision_and_returns_new_revision():
    slot = _slot()
    initial = slot_revision(slot)
    response, assignments, slots, leader_id = await _call(slot, revision=initial)
    assert response.leader_id == leader_id
    assert response.status == AssignmentStatus.ASSIGNED
    assert response.event_revision == slot_revision(slot)
    assert response.event_revision != initial
    assignments.save.assert_awaited_once()
    slots.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_inline_rejects_missing_revision_before_any_write():
    with pytest.raises(HTTPException) as error:
        await _call(_slot(), revision=None)
    assert error.value.status_code == 428


@pytest.mark.asyncio
async def test_inline_rejects_stale_revision_before_any_write():
    with pytest.raises(HTTPException) as error:
        await _call(_slot(), revision='"stale"')
    assert error.value.status_code == 412


@pytest.mark.asyncio
async def test_inline_enforces_planner_permission():
    slot = _slot()
    with pytest.raises(HTTPException) as error:
        await _call(slot, revision=slot_revision(slot), permitted=False)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_inline_preserves_warning_conflicts_without_mutation():
    slot = _slot()
    with pytest.raises(HTTPException) as error:
        await _call(slot, revision=slot_revision(slot), conflict=True)
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_invited_congregation_cannot_mutate_host_assignment():
    slot = _slot()
    slot.invitation_source_event_id = uuid.uuid4()
    with pytest.raises(HTTPException) as error:
        await _call(slot, revision=slot_revision(slot))
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_cancelled_planning_slot_rejects_inline_assignment():
    slot = _slot()
    slot.status = PlanningSlotStatus.CANCELLED
    with pytest.raises(HTTPException) as error:
        await _call(slot, revision=slot_revision(slot))
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_inline_updates_assignment_without_removing_historical_record():
    slot = _slot()
    existing = ServiceAssignment.create(event_id=slot.id, leader_id=uuid.uuid4(),
                                         status=AssignmentStatus.CONFIRMED)
    original_id = existing.id
    response, assignments, slots, leader_id = await _call(
        slot, revision=slot_revision(slot), existing=[existing],
    )
    assert response.id == original_id
    assert response.leader_id == leader_id
    assert response.status == AssignmentStatus.ASSIGNED
    assignments.save.assert_awaited_once_with(existing)
    slots.save.assert_awaited_once()


def test_inline_does_not_allow_implicit_deletion_or_unknown_workflow_fields():
    with pytest.raises(ValidationError):
        InlineAssignmentChange.model_validate({"leader_id": None})
    with pytest.raises(ValidationError):
        InlineAssignmentChange.model_validate({
            "leader_id": str(uuid.uuid4()),
            "status": "CONFIRMED",
        })


def _instance(slot: PlanningSlot) -> EventInstance:
    return EventInstance.create(
        planning_slot_id=slot.id,
        title="Gottesdienst",
        actual_start_at=datetime(2026, 10, 14, 10, tzinfo=UTC),
        actual_end_at=datetime(2026, 10, 14, 11, tzinfo=UTC),
        source=EventSource.INTERNAL,
        visibility=EventVisibility.PUBLIC,
    )


def test_assignment_revision_matches_complete_event_snapshot():
    slot = _slot()
    instance = _instance(slot)
    from app.adapters.api.routers.events import slot_revision

    assert slot_revision(slot, instance) == slot_revision(slot, instance)
    before = slot_revision(slot, instance)
    instance.updated_at = datetime(2026, 10, 15, tzinfo=UTC)
    assert slot_revision(slot, instance) != before


@pytest.mark.asyncio
async def test_assignment_rejects_instance_only_stale_revision():
    slot = _slot()
    instance = _instance(slot)
    before = slot_revision(slot, instance)
    instance.updated_at = datetime(2026, 10, 15, tzinfo=UTC)
    slots, assignments, instances = AsyncMock(), AsyncMock(), AsyncMock()
    slots.get_for_update.return_value = slot
    instances.get_by_planning_slot.return_value = instance
    with (
        patch.object(service_assignments, "require_role_in_district"),
        pytest.raises(HTTPException) as exc,
    ):
        await service_assignments.inline_change_assignment(
            slot.id, InlineAssignmentChange(leader_id=uuid.uuid4()),
            object(), AsyncMock(), if_match=before,
            slots=slots, assignments_repo=assignments, instance_repo=instances,
        )
    assert exc.value.status_code == 412
    assignments.save.assert_not_awaited()


def test_inserting_instance_invalidates_slot_only_revision():
    slot = _slot()
    before = slot_revision(slot)
    assert slot_revision(slot, _instance(slot)) != before
