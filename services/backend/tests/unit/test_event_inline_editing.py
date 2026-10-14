# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Conditional event-inline editing: do not bypass role, ownership or version checks."""

import uuid
from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.routers import events
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_slot import PlanningSlot, ReleasedEventError
from app.domain.models.role import Role


def _context():
    slot = PlanningSlot.create(
        district_id=uuid.uuid4(), planning_date=date(2026, 10, 12),
        planning_time=time(10, 0), title="Vorher", category="Gottesdienst",
    )
    instance = EventInstance.create(
        planning_slot_id=slot.id, title="Vorher",
        actual_start_at=datetime(2026, 10, 12, 10, tzinfo=UTC),
        actual_end_at=datetime(2026, 10, 12, 11, tzinfo=UTC),
        source=EventSource.INTERNAL, visibility=EventVisibility.PUBLIC,
    )
    auth = SimpleNamespace(user=SimpleNamespace(is_superadmin=True), memberships=[])
    slot_repo, inst_repo, cong_repo, assignments_repo, leaders_repo = (
        AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    )
    slot_repo.get_for_update.return_value = slot
    inst_repo.get_by_planning_slot.return_value = instance
    return slot, instance, auth, slot_repo, inst_repo, cong_repo, assignments_repo, leaders_repo


async def _update(context, body, revision):
    slot, _, auth, slots, instances, congregations, assignments, leaders = context
    with (
        patch.object(events, "require_role_in_district") as require_role,
        patch.object(events, "_load_responsible", AsyncMock(return_value={})),
    ):
        result = await events.inline_update_event(
            slot.id, body, auth, AsyncMock(), if_match=revision,
            slot_repo=slots, inst_repo=instances, cong_repo=congregations,
            assignments_repo=assignments, leaders_repo=leaders,
        )
    assert require_role.call_count == 2
    require_role.assert_any_call(auth, Role.PLANNER, slot.district_id)
    return result


@pytest.mark.asyncio
async def test_conditional_inline_title_save_increments_revision_and_updates_instance():
    ctx = _context()
    before = events._slot_revision(ctx[0])
    result = await _update(ctx, events.EventUpdate(title="Neu"), before)
    assert result.title == "Neu"
    assert result.revision != before
    assert result.revision.startswith('"')
    assert ctx[1].title == "Neu"
    assert ctx[3].get_for_update.await_count == 2
    ctx[3].get_for_update.assert_any_await(ctx[0].id)
    ctx[3].save.assert_awaited_once()


@pytest.mark.asyncio
async def test_description_can_be_cleared_and_still_has_a_new_revision():
    ctx = _context()
    ctx[1].description = "Alt"
    result = await _update(ctx, events.EventUpdate(description=None), events._slot_revision(ctx[0]))
    assert result.description is None
    ctx[3].save.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_precondition_is_428_and_does_not_load_event():
    ctx = _context()
    with pytest.raises(HTTPException) as err:
        await _update(ctx, events.EventUpdate(title="Änderung"), None)
    assert err.value.status_code == 428
    ctx[3].get_for_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_revision_is_412_without_any_writes():
    ctx = _context()
    with pytest.raises(HTTPException) as err:
        await _update(ctx, events.EventUpdate(title="Neu"), '"stale"')
    assert err.value.status_code == 412
    ctx[3].save.assert_not_awaited()
    ctx[4].save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [
    {"status": "CANCELLED"},
    {"congregation_id": str(uuid.uuid4())},
    {"start_at": datetime(2026, 10, 12, 11, tzinfo=UTC).isoformat()},
])
async def test_workflow_fields_are_rejected_by_the_inline_contract(payload):
    ctx = _context()
    with pytest.raises(ValidationError):
        events.EventInlineUpdate.model_validate(payload)
    ctx[3].save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [
    events.EventInlineUpdate(title=None),
    events.EventInlineUpdate(),
])
async def test_invalid_inline_payloads_are_never_mutated(body):
    ctx = _context()
    with pytest.raises(HTTPException) as err:
        await _update(ctx, body, events._slot_revision(ctx[0]))
    assert err.value.status_code == 422
    ctx[3].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_external_authority_is_denied():
    ctx = _context()
    ctx[1].source = EventSource.EXTERNAL
    with pytest.raises(HTTPException) as err:
        await _update(ctx, events.EventUpdate(title="Neu"), events._slot_revision(ctx[0]))
    assert err.value.status_code == 403
    ctx[3].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_event_is_404():
    ctx = _context()
    ctx[3].get_for_update.return_value = None
    with pytest.raises(HTTPException) as err:
        await _update(ctx, events.EventUpdate(title="Neu"), events._slot_revision(ctx[0]))
    assert err.value.status_code == 404


@pytest.mark.asyncio
async def test_permission_failure_stops_writes():
    ctx = _context()
    with (
        patch.object(events, "require_role_in_district", side_effect=HTTPException(403)),
        patch.object(events, "_load_responsible", AsyncMock(return_value={})),
        pytest.raises(HTTPException) as err,
    ):
        await events.inline_update_event(
            ctx[0].id, events.EventUpdate(title="Neu"), ctx[2], AsyncMock(),
            if_match=events._slot_revision(ctx[0]),
            slot_repo=ctx[3], inst_repo=ctx[4], cong_repo=ctx[5],
            assignments_repo=ctx[6], leaders_repo=ctx[7],
        )
    assert err.value.status_code == 403
    ctx[3].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_business_conflict_remains_409_not_412():
    ctx = _context()
    ctx[3].save.side_effect = ReleasedEventError("Freigegeben")
    with pytest.raises(HTTPException) as err:
        await _update(ctx, events.EventUpdate(title="Neu"), events._slot_revision(ctx[0]))
    assert err.value.status_code == 409
