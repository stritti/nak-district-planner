# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Dependent event changes: If-Match contract, server-side revalidation and impact preview."""

import uuid
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import events
from app.adapters.api.schemas import events as event_schemas
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
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
def _patches(conflicts: list[ConflictResult] | None = None, accounts: dict | None = None):
    """``accounts`` maps leader IDs to their linked account (none linked by default)."""
    leaders = MagicMock()
    leaders.get = AsyncMock(
        side_effect=lambda leader_id: SimpleNamespace(user_sub=(accounts or {}).get(leader_id))
    )
    mocks = {
        "get_leader_repository": AsyncMock(return_value=leaders),
        "acquire_account_xact_lock": AsyncMock(),
        "require_role_in_district": MagicMock(),
        "ensure_leader_in_district": AsyncMock(),
        "acquire_advisory_xact_lock": AsyncMock(),
        "check_service_assignment_conflicts": AsyncMock(return_value=list(conflicts or [])),
    }
    with patch.multiple(events, **mocks):
        yield {**mocks, "leaders_repo": leaders}


def _default_leaders_repo():
    repo = MagicMock()
    repo.get = AsyncMock(return_value=None)
    return repo


async def _update(slot, repos, body, if_match=None, duties_repo=None, leaders_repo=None):
    slot_repo, inst_repo, assignments_repo = repos
    return await events.update_event(
        slot.id,
        body,
        object(),
        AsyncMock(),
        slot_repo=slot_repo,
        inst_repo=inst_repo,
        assignments_repo=assignments_repo,
        leaders_repo=leaders_repo if leaders_repo is not None else _default_leaders_repo(),
        duties_repo=duties_repo if duties_repo is not None else _duties_repo(slot),
        if_match=if_match,
    )


@pytest.mark.asyncio
async def test_dependent_change_without_if_match_is_precondition_required() -> None:
    slot = _slot()
    repos = _repos(slot)
    with _patches():
        with pytest.raises(HTTPException) as error:
            await _update(slot, repos, event_schemas.EventUpdate(start_at=NEW_START))
    assert error.value.status_code == 428
    repos[0].save.assert_not_awaited()
    repos[0].get.assert_not_awaited()
    repos[0].get_for_update.assert_not_awaited()
    repos[1].get_by_planning_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_dependent_change_with_stale_revision_is_rejected() -> None:
    slot = _slot()
    repos = _repos(slot)
    with _patches():
        with pytest.raises(HTTPException) as error:
            await _update(slot, repos, event_schemas.EventUpdate(start_at=NEW_START), if_match='"stale"')
    assert error.value.status_code == 412
    repos[0].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_dependent_change_still_requires_if_match() -> None:
    slot = _slot()
    repos = _repos(slot)
    with _patches():
        with pytest.raises(HTTPException) as exc:
            await _update(slot, repos, event_schemas.EventUpdate(title="Neu"))
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
                event_schemas.EventUpdate(start_at=NEW_START),
                if_match=events.slot_revision(slot),
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
                event_schemas.EventUpdate(start_at=NEW_START),
                if_match=events.slot_revision(slot),
            )
        assert error.value.status_code == 409
        repos[0].save.assert_not_awaited()

        result = await _update(
            slot,
            repos,
            event_schemas.EventUpdate(start_at=NEW_START, confirm_warnings=True),
            if_match=events.slot_revision(slot),
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
                event_schemas.EventUpdate(start_at=NEW_START),
                if_match=events.slot_revision(slot),
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
            event_schemas.EventUpdate(start_at=NEW_START),
            if_match=events.slot_revision(slot),
        )
    locked = [call.args[1] for call in mocks["acquire_advisory_xact_lock"].await_args_list]
    assert locked == sorted(locked, key=str)
    assert len(locked) == 2


@pytest.mark.asyncio
async def test_revalidation_locks_linked_accounts_after_all_leaders() -> None:
    slot = _slot()
    assignments = [_assigned(slot), _assigned(slot), _assigned(slot)]
    accounts = {assignments[0].leader_id: "sub-b", assignments[1].leader_id: "sub-a"}
    repos = _repos(slot, assignments)
    order = MagicMock()
    with _patches(accounts=accounts) as mocks:
        order.attach_mock(mocks["acquire_advisory_xact_lock"], "leader")
        order.attach_mock(mocks["acquire_account_xact_lock"], "account")
        await _update(
            slot,
            repos,
            event_schemas.EventUpdate(start_at=NEW_START),
            if_match=events.slot_revision(slot),
            leaders_repo=mocks["leaders_repo"],
        )
    kinds = [name for name, _, _ in order.mock_calls]
    assert kinds == ["leader"] * 3 + ["account"] * 2
    assert [c.args[1] for c in mocks["acquire_account_xact_lock"].await_args_list] == [
        "sub-a",
        "sub-b",
    ]


@pytest.mark.asyncio
async def test_preview_reports_warning_impact_without_writing() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot, [_assigned(slot)])
    with _patches([_conflict(Severity.WARN)]):
        result = await events.preview_event_change(
            slot.id,
            event_schemas.EventChangeImpactRequest(start_at=NEW_START),
            object(),
            AsyncMock(),
            if_match=events.slot_revision(slot),
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
            event_schemas.EventChangeImpactRequest(start_at=NEW_START),
            object(),
            AsyncMock(),
            if_match=events.slot_revision(slot),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
        )
    assert result.blocked is True


def _duties_repo(slot: PlanningSlot, assignments=()) -> MagicMock:
    from app.domain.models.event_duty import EventDutyCategory

    categories = EventDutyCategory.defaults(slot.district_id)
    repo = MagicMock()
    repo.catalog = AsyncMock(return_value=(categories, []))
    repo.list_assignments = AsyncMock(return_value=list(assignments))
    repo.categories = categories
    return repo


@pytest.mark.asyncio
async def test_preview_reports_duties_flagged_by_category_change() -> None:
    from app.domain.models.event_duty import EventDutyAssignment

    slot = _slot()
    slot.category = "Gottesdienst"
    slot_repo, inst_repo, assignments_repo = _repos(slot)
    duties = _duties_repo(slot)
    organist = next(c for c in duties.categories if c.code == "organist")
    duties.list_assignments.return_value = [
        EventDutyAssignment.create(slot.id, organist, slot.congregation_id, name="Anna")
    ]
    with _patches():
        result = await events.preview_event_change(
            slot.id,
            event_schemas.EventChangeImpactRequest(category="Feiertag"),
            object(),
            AsyncMock(),
            if_match=events.slot_revision(slot),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
            duties_repo=duties,
        )
    assert result.duties_newly_flagged == 1
    assert result.duties_quarantined_after == 0
    assert result.blocked is False
    slot_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_preview_skips_duty_lookup_for_pure_schedule_changes() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot)
    duties = _duties_repo(slot)
    with _patches():
        result = await events.preview_event_change(
            slot.id,
            event_schemas.EventChangeImpactRequest(start_at=NEW_START),
            object(),
            AsyncMock(),
            if_match=events.slot_revision(slot),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
            duties_repo=duties,
        )
    assert result.duties_newly_flagged == 0
    duties.list_assignments.assert_not_awaited()


@pytest.mark.asyncio
async def test_preview_without_assignments_has_no_impact() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot)
    with _patches():
        result = await events.preview_event_change(
            slot.id,
            event_schemas.EventChangeImpactRequest(congregation_id=None),
            object(),
            AsyncMock(),
            if_match=events.slot_revision(slot),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
            duties_repo=_duties_repo(slot),
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
                event_schemas.EventChangeImpactRequest(start_at=NEW_START),
                object(),
                AsyncMock(),
            if_match=events.slot_revision(slot),
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
            event_schemas.EventChangeImpactRequest(
                start_at=NEW_START, end_at=datetime(2026, 10, 20, 8, tzinfo=UTC)
            ),
            object(),
            AsyncMock(),
            if_match=events.slot_revision(slot),
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
                    event_schemas.EventChangeImpactRequest(start_at=NEW_START),
                    object(), AsyncMock(), if_match=revision,
                    slot_repo=slot_repo, inst_repo=inst_repo,
                    assignments_repo=assignments_repo,
                )
            assert exc.value.status_code == expected
    mocks["check_service_assignment_conflicts"].assert_not_awaited()
    slot_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocking_impact_is_checked_before_any_instance_write() -> None:
    slot = _slot()
    instance = EventInstance.create(
        planning_slot_id=slot.id,
        title="Gottesdienst",
        actual_start_at=datetime(2026, 10, 14, 10, tzinfo=UTC),
        actual_end_at=datetime(2026, 10, 14, 11, tzinfo=UTC),
        source=EventSource.INTERNAL,
        visibility=EventVisibility.PUBLIC,
    )
    repos = _repos(slot, [_assigned(slot)])
    repos[1].get_by_planning_slot.return_value = instance
    with _patches([_conflict(Severity.BLOCK)]), pytest.raises(HTTPException) as exc:
        await _update(
            slot, repos, event_schemas.EventUpdate(start_at=NEW_START, end_at=NEW_START.replace(hour=10)),
            if_match=events.slot_revision(slot, instance),
        )
    assert exc.value.status_code == 409
    repos[1].save.assert_not_awaited()
    repos[0].save.assert_not_awaited()


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (event_schemas.EventUpdate(title="Neu"), False),
        (event_schemas.EventUpdate(category="Vortrag"), False),
        (event_schemas.EventUpdate(congregation_id=None), False),
        (event_schemas.EventUpdate(start_at=datetime(2026, 10, 14, 10, tzinfo=UTC)), False),
        (event_schemas.EventUpdate(start_at=NEW_START), True),
        (event_schemas.EventUpdate(congregation_id=uuid.uuid4()), True),
        (event_schemas.EventUpdate(end_at=NEW_START), False),
    ],
)
def test_dependency_trigger_uses_explicit_effective_fields_without_instance(body, expected):
    assert events._changes_service_dependencies(_slot(), None, body) is expected


def test_dependency_trigger_compares_instance_schedule_and_explicit_congregation_clear():
    slot = _slot()
    slot.congregation_id = uuid.uuid4()
    instance = EventInstance.create(
        planning_slot_id=slot.id, title="Gottesdienst",
        actual_start_at=NEW_START, actual_end_at=NEW_START.replace(hour=10),
        source=EventSource.INTERNAL, visibility=EventVisibility.PUBLIC,
    )
    assert not events._changes_service_dependencies(
        slot, instance, event_schemas.EventUpdate(start_at=NEW_START, end_at=NEW_START.replace(hour=10)),
    )
    assert events._changes_service_dependencies(
        slot, instance, event_schemas.EventUpdate(end_at=NEW_START.replace(hour=11)),
    )
    assert events._changes_service_dependencies(
        slot, instance, event_schemas.EventUpdate(congregation_id=None),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("preview", [False, True])
async def test_end_only_slot_change_rejects_end_before_effective_planned_start(preview):
    slot = _slot()
    repos = _repos(slot)
    end = datetime(2026, 10, 14, 9, tzinfo=UTC)
    with _patches(), pytest.raises(HTTPException) as exc:
        if preview:
            await events.preview_event_change(
                slot.id, event_schemas.EventChangeImpactRequest(end_at=end),
                object(), AsyncMock(), if_match=events.slot_revision(slot),
                slot_repo=repos[0], inst_repo=repos[1], assignments_repo=repos[2],
            )
        else:
            await _update(
                slot, repos, event_schemas.EventUpdate(end_at=end),
                if_match=events.slot_revision(slot),
            )
    assert exc.value.status_code == 400
    assert "wirksamen Startzeit" in exc.value.detail
    repos[0].save.assert_not_awaited()
    repos[1].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_scalar_update_does_not_revalidate_existing_leader_ownership():
    slot = _slot()
    repos = _repos(slot, [_assigned(slot)])
    with _patches() as mocks:
        mocks["ensure_leader_in_district"].side_effect = HTTPException(
            status_code=422, detail="Invalid historic leader reference",
        )
        result = await _update(
            slot, repos, event_schemas.EventUpdate(title="Neuer Titel"),
            if_match=events.slot_revision(slot),
        )
    assert result.title == "Neuer Titel"
    mocks["ensure_leader_in_district"].assert_not_awaited()
    mocks["acquire_advisory_xact_lock"].assert_not_awaited()
    mocks["check_service_assignment_conflicts"].assert_not_awaited()
    repos[0].save.assert_awaited_once()


def _slot_with_organist(*, category: str = "Gottesdienst"):
    """A slot with one organist duty that a category change would flag for review."""
    from app.domain.models.event_duty import EventDutyAssignment

    slot = _slot()
    slot.category = category
    slot.congregation_id = uuid.uuid4()
    duties = _duties_repo(slot)
    organist = next(c for c in duties.categories if c.code == "organist")
    duties.list_assignments.return_value = [
        EventDutyAssignment.create(slot.id, organist, slot.congregation_id, name="Anna")
    ]
    return slot, duties


@pytest.mark.asyncio
async def test_direct_patch_without_preview_cannot_flag_duties_silently() -> None:
    slot, duties = _slot_with_organist()
    repos = _repos(slot)
    with _patches():
        with pytest.raises(HTTPException) as error:
            await _update(
                slot, repos, event_schemas.EventUpdate(category="Feiertag"),
                if_match=events.slot_revision(slot), duties_repo=duties,
            )
    assert error.value.status_code == 409
    assert error.value.detail["code"] == "duty_impact_unacknowledged"
    assert error.value.detail["duties_newly_flagged"] == 1
    assert slot.category == "Gottesdienst"
    repos[0].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_patch_with_matching_acknowledgement_is_applied() -> None:
    slot, duties = _slot_with_organist()
    repos = _repos(slot)
    body = event_schemas.EventUpdate(
        category="Feiertag",
        acknowledged_duty_impact=event_schemas.DutyImpactAcknowledgement(newly_flagged=1, newly_quarantined=0),
    )
    with _patches():
        await _update(slot, repos, body, if_match=events.slot_revision(slot), duties_repo=duties)
    assert slot.category == "Feiertag"
    repos[0].save.assert_awaited_once()


@pytest.mark.asyncio
async def test_duty_added_after_preview_invalidates_the_acknowledgement() -> None:
    """Duty writes do not change the event revision; the PATCH must recompute the impact."""
    from app.domain.models.event_duty import EventDutyAssignment

    slot, duties = _slot_with_organist()
    conductor = next(c for c in duties.categories if c.code == "conductor")
    duties.list_assignments.return_value.append(
        EventDutyAssignment.create(slot.id, conductor, slot.congregation_id, name="Berta")
    )
    repos = _repos(slot)
    previewed = event_schemas.DutyImpactAcknowledgement(newly_flagged=1, newly_quarantined=0)
    with _patches():
        with pytest.raises(HTTPException) as error:
            await _update(
                slot, repos,
                event_schemas.EventUpdate(category="Feiertag", acknowledged_duty_impact=previewed),
                if_match=events.slot_revision(slot), duties_repo=duties,
            )
    assert error.value.status_code == 409
    assert error.value.detail["duties_newly_flagged"] == 2
    repos[0].save.assert_not_awaited()


@pytest.mark.asyncio
async def test_congregation_move_quarantine_requires_acknowledgement() -> None:
    slot, duties = _slot_with_organist()
    repos = _repos(slot)
    with _patches():
        with pytest.raises(HTTPException) as error:
            await _update(
                slot, repos, event_schemas.EventUpdate(congregation_id=uuid.uuid4()),
                if_match=events.slot_revision(slot), duties_repo=duties,
            )
    assert error.value.status_code == 409
    assert error.value.detail["duties_newly_quarantined"] == 1


@pytest.mark.asyncio
async def test_changes_without_scope_impact_never_touch_duties() -> None:
    slot, duties = _slot_with_organist()
    repos = _repos(slot)
    with _patches():
        await _update(
            slot, repos, event_schemas.EventUpdate(title="Neu", category="Gottesdienst"),
            if_match=events.slot_revision(slot), duties_repo=duties,
        )
    duties.list_assignments.assert_not_awaited()


@pytest.mark.asyncio
async def test_category_only_preview_ignores_historic_leader_blocks() -> None:
    slot = _slot()
    slot_repo, inst_repo, assignments_repo = _repos(slot, [_assigned(slot)])
    with _patches([_conflict(Severity.BLOCK)]) as mocks:
        result = await events.preview_event_change(
            slot.id,
            event_schemas.EventChangeImpactRequest(category="Jugendstunde"),
            object(),
            AsyncMock(),
            if_match=events.slot_revision(slot),
            slot_repo=slot_repo,
            inst_repo=inst_repo,
            assignments_repo=assignments_repo,
            duties_repo=_duties_repo(slot),
        )
    assert result.blocked is False
    assert result.items == []
    mocks["check_service_assignment_conflicts"].assert_not_awaited()
