# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Dependent event changes: If-Match contract, server-side revalidation and impact preview."""

import uuid
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import events
from app.domain.models.planning_slot import PlanningSlot
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment
from app.domain.planning.conflict_result import ConflictResult, Severity

NEW_START = datetime(2026, 10, 20, 9, tzinfo=UTC)


def _slot() -> PlanningSlot:
    return PlanningSlot.create(
        district_id=uuid.uuid4(),
        planning_date=date(2026, 10, 14),
        planning_time=time(10),
        title="Gottesdienst",
    )


def _assigned(slot: PlanningSlot, leader_id: uuid.UUID | None = None) -> ServiceAssignment:
    return ServiceAssignment.create(
        event_id=slot.id,
        leader_id=leader_id or uuid.uuid4(),
        status=AssignmentStatus.ASSIGNED,
    )


def _conflict(severity: Severity) -> ConflictResult:
    return ConflictResult(
        rule_id="test_rule", severity=severity, message=f"Konflikt {severity.value}"
    )


def _repos(slot: PlanningSlot, assignments: list[ServiceAssignment] | None = None):
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    slot_repo.get_for_update.return_value = slot
    inst_repo = AsyncMock()
    inst_repo.get_by_planning_slot.return_value = None
    assignments_repo = AsyncMock()
    assignments_repo.list_by_planning_slot.return_value = list(assignments or [])
    return slot_repo, inst_repo, assignments_repo


@contextmanager
def _patches(conflicts: list[ConflictResult] | None = None):
    mocks = {
        "require_role_in_district": MagicMock(),
        "ensure_leader_in_district": AsyncMock(),
        "acquire_advisory_xact_lock": AsyncMock(),
        "check_service_assignment_conflicts": AsyncMock(return_value=list(conflicts or [])),
    }
    with patch.multiple(events, **mocks):
        yield mocks


async def _update(slot, repos, body, if_match=None):
    slot_repo, inst_repo, assignments_repo = repos
    return await events.update_event(
        slot.id,
        body,
        object(),
        AsyncMock(),
        slot_repo=slot_repo,
        inst_repo=inst_repo,
        assignments_repo=assignments_repo,
        if_match=if_match,
    )


@pytest.mark.asyncio
async def test_dependent_change_without_if_match_is_precondition_required() -> None:
    slot = _slot()
    repos = _repos(slot)
    with _patches():
        with pytest.raises(HTTPException) as error:
            await _update(slot, repos, events.EventUpdate(start_at=NEW_START))
    assert error.value.status_code == 428
    repos[0].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_dependent_change_with_stale_revision_is_rejected() -> None:
    slot = _slot()
    repos = _repos(slot)
    with _patches():
        with pytest.raises(HTTPException) as error:
            await _update(slot, repos, events.EventUpdate(start_at=NEW_START), if_match='"stale"')
    assert error.value.status_code == 412
    repos[0].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_dependent_change_still_requires_if_match() -> None:
    slot = _slot()
    repos = _repos(slot)
    with _patches():
        with pytest.raises(HTTPException) as exc:
            await _update(slot, repos, events.EventUpdate(title="Neu"))
    assert exc.value.status_code == 428
    repos[0].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocking_conflict_rejects_change_before_save() -> None:
    slot = _slot()
    repos = _repos(slot, [_assigned(slot)])
    with _patches([_conflict(Severity.BLOCK)]):
        with pytest.raises(HTTPException) as error:
            await _update(
                slot,
                repos,
                events.EventUpdate(start_at=NEW_START),
                if_match=events._slot_revision(slot),
            )
    assert error.value.status_code == 409
    assert error.value.detail["conflicts"][0]["severity"] == "BLOCK"
    repos[0].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_warning_conflict_requires_explicit_confirmation() -> None:
    slot = _slot()
    repos = _repos(slot, [_assigned(slot)])
    with _patches([_conflict(Severity.WARN)]):
        with pytest.raises(HTTPException) as error:
            await _update(
                slot,
                repos,
                events.EventUpdate(start_at=NEW_START),
                if_match=events._slot_revision(slot),
            )
        assert error.value.status_code == 409
        repos[0].save.assert_not_awaited()

        result = await _update(
            slot,
            repos,
            events.EventUpdate(start_at=NEW_START, confirm_warnings=True),
            if_match=events._slot_revision(slot),
        )
    assert result.start_at == NEW_START
    repos[0].save.assert_awaited_once()


@pytest.mark.asyncio
async def test_responsible_leader_outside_district_is_rejected() -> None:
    slot = _slot()
    repos = _repos(slot, [_assigned(slot)])
    with _patches() as mocks:
        mocks["ensure_leader_in_district"].side_effect = HTTPException(
            status_code=422, detail="leader"
        )
        with pytest.raises(HTTPException) as error:
            await _update(
                slot,
                repos,
                events.EventUpdate(start_at=NEW_START),
                if_match=events._slot_revision(slot),
            )
    assert error.value.status_code == 422
    repos[0].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_revalidation_locks_leaders_in_id_order() -> None:
    slot = _slot()
    assignments = [_assigned(slot), _assigned(slot)]
    repos = _repos(slot, assignments)
    with _patches() as mocks:
        await _update(
            slot,
            repos,
            events.EventUpdate(start_at=NEW_START),
            if_match=events._slot_revision(slot),
        )
    locked = [call.args[1] for call in mocks["acquire_advisory_xact_lock"].await_args_list]
    assert locked == sorted(locked, key=str)
    assert len(locked) == 2


@pytest.mark.asyncio
async def test_preview_reports_warning_impact_without_writing() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot, [_assigned(slot)])
    with _patches([_conflict(Severity.WARN)]):
        result = await events.preview_event_change(
            slot.id,
            events.EventChangeImpactRequest(start_at=NEW_START),
            object(),
            AsyncMock(),
            if_match=events._slot_revision(slot),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
        )
    assert result.requires_confirmation is True
    assert result.blocked is False
    assert len(result.items) == 1
    slot_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_preview_reports_blocking_impact() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot, [_assigned(slot)])
    with _patches([_conflict(Severity.BLOCK)]):
        result = await events.preview_event_change(
            slot.id,
            events.EventChangeImpactRequest(start_at=NEW_START),
            object(),
            AsyncMock(),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
        )
    assert result.blocked is True


@pytest.mark.asyncio
async def test_preview_without_assignments_has_no_impact() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot)
    with _patches():
        result = await events.preview_event_change(
            slot.id,
            events.EventChangeImpactRequest(congregation_id=None),
            object(),
            AsyncMock(),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
        )
    assert result.blocked is False
    assert result.requires_confirmation is False
    assert result.items == []


@pytest.mark.asyncio
async def test_preview_requires_planner_role() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot)
    with _patches() as mocks:
        mocks["require_role_in_district"].side_effect = HTTPException(status_code=403, detail="no")
        with pytest.raises(HTTPException) as error:
            await events.preview_event_change(
                slot.id,
                events.EventChangeImpactRequest(start_at=NEW_START),
                object(),
                AsyncMock(),
                slot_repo=slot_repo,
                inst_repo=inst_repo,
                assignments_repo=assignments_repo,
            )
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_preview_rejects_end_before_start() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot)
    with _patches(), pytest.raises(HTTPException) as error:
        await events.preview_event_change(
            slot.id,
            events.EventChangeImpactRequest(
                start_at=NEW_START, end_at=datetime(2026, 10, 20, 8, tzinfo=UTC)
            ),
            object(),
            AsyncMock(),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
        )
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_impact_preview_rejects_missing_and_stale_snapshot() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot, [_assigned(slot)])
    with _patches() as mocks:
        for revision, expected in ((None, 428), ('"stale"', 412)):
            with pytest.raises(HTTPException) as exc:
                await events.preview_event_change(
                    slot.id,
                    events.EventChangeImpactRequest(start_at=NEW_START),
                    object(), AsyncMock(), if_match=revision,
                    slot_repo=slot_repo, inst_repo=inst_repo,
                    assignments_repo=assignments_repo,
                )
            assert exc.value.status_code == expected
    mocks["check_service_assignment_conflicts"].assert_not_awaited()
    slot_repo.save.assert_not_awaited()
