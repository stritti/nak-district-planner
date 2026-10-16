# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Dialog/legacy assignment writers share the event's strong revision with inline cells.

Without this a dialog save could silently overwrite an inline assignment (lost update).
428 = no precondition, 412 = the event changed since the client read it.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.revisions import slot_revision
from app.adapters.api.routers import service_assignments as router
from app.adapters.api.schemas.service_assignment import (
    InlineAssignmentResult,
    ServiceAssignmentCreate,
    ServiceAssignmentUpdate,
)
from app.domain.models.service_assignment import ServiceAssignment
from tests.unit.assignment_preconditions import precondition
from tests.unit.test_router_leaders_events_assignments import _auth_context, _planning_slot

ACTIONS = ("create", "update", "delete")


def _setup():
    slot = _planning_slot()
    assignment = ServiceAssignment.create(event_id=slot.id, leader_name="Pr. X")
    slots = AsyncMock()
    slots.get_for_update.return_value = slot
    repo = AsyncMock()
    repo.get.return_value = assignment
    return slot, assignment, slots, repo


async def _call(action, slot, assignment, slots, repo, **kwargs):
    args = (_auth_context(), AsyncMock(), slots, repo)
    with (
        patch.object(router, "require_role_in_district"),
        patch.object(router, "_check_typed_name", new=AsyncMock()),
    ):
        if action == "create":
            return await router.create_assignment(
                slot.id, ServiceAssignmentCreate(leader_name="Pr. Y"), *args, **kwargs
            )
        if action == "update":
            return await router.update_assignment(
                slot.id, assignment.id, ServiceAssignmentUpdate(leader_name="Pr. Z"), *args, **kwargs
            )
        return await router.delete_assignment(slot.id, assignment.id, *args, **kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ACTIONS)
async def test_missing_precondition_is_428_and_nothing_is_written(action):
    slot, assignment, slots, repo = _setup()
    kwargs = precondition(slot)
    kwargs["if_match"] = None
    with pytest.raises(HTTPException) as error:
        await _call(action, slot, assignment, slots, repo, **kwargs)
    assert error.value.status_code == 428
    repo.save.assert_not_awaited()
    repo.delete.assert_not_awaited()
    slots.save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ACTIONS)
async def test_stale_precondition_is_412_and_nothing_is_written(action):
    slot, assignment, slots, repo = _setup()
    kwargs = precondition(slot)
    kwargs["if_match"] = '"stale"'
    with pytest.raises(HTTPException) as error:
        await _call(action, slot, assignment, slots, repo, **kwargs)
    assert error.value.status_code == 412
    repo.save.assert_not_awaited()
    repo.delete.assert_not_awaited()
    slots.save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ACTIONS)
async def test_revision_includes_the_event_instance(action):
    """A change to the instance alone (e.g. a time move) invalidates the client's snapshot."""
    from app.domain.models.event_instance import EventInstance

    slot, assignment, slots, repo = _setup()
    instance = EventInstance.__new__(EventInstance)
    instance.updated_at = slot.updated_at
    kwargs = precondition(slot, instance=None)  # client read the slot before the instance existed
    kwargs["instance_repo"].get_by_planning_slot.return_value = instance
    assert slot_revision(slot, instance) != kwargs["if_match"]
    with pytest.raises(HTTPException) as error:
        await _call(action, slot, assignment, slots, repo, **kwargs)
    assert error.value.status_code == 412


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["create", "update"])
async def test_success_returns_the_fresh_event_revision(action):
    slot, assignment, slots, repo = _setup()
    kwargs = precondition(slot)
    before = kwargs["if_match"]
    result = await _call(action, slot, assignment, slots, repo, **kwargs)
    assert isinstance(result, InlineAssignmentResult)
    assert result.event_revision == slot_revision(slot, None)
    assert result.event_revision != before, "the write must advance the event revision"


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ACTIONS)
async def test_permission_is_checked_before_the_precondition(action):
    slot, assignment, slots, repo = _setup()
    kwargs = precondition(slot)
    kwargs["if_match"] = None
    denied = HTTPException(status_code=403)
    with (
        patch.object(router, "require_role_in_district", side_effect=denied),
        pytest.raises(HTTPException) as error,
    ):
        if action == "create":
            await router.create_assignment(
                slot.id, ServiceAssignmentCreate(leader_name="Pr. Y"),
                _auth_context(), AsyncMock(), slots, repo, **kwargs,
            )
        elif action == "update":
            await router.update_assignment(
                slot.id, assignment.id, ServiceAssignmentUpdate(leader_name="Z"),
                _auth_context(), AsyncMock(), slots, repo, AsyncMock(), **kwargs,
            )
        else:
            await router.delete_assignment(
                slot.id, assignment.id, _auth_context(), AsyncMock(), slots, repo, **kwargs,
            )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_unknown_event_is_404_without_evaluating_the_precondition():
    slots = AsyncMock()
    slots.get_for_update.return_value = None
    kwargs = precondition(_planning_slot())
    with pytest.raises(HTTPException) as error:
        await router.create_assignment(
            uuid.uuid4(), ServiceAssignmentCreate(leader_name="X"),
            _auth_context(), AsyncMock(), slots, AsyncMock(), **kwargs,
        )
    assert error.value.status_code == 404
    kwargs["instance_repo"].get_by_planning_slot.assert_not_awaited()
