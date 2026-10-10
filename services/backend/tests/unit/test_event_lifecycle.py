"""Release boundary and manual event CRUD regressions."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.api.routers import events
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
    ReleasedEventError,
)
from app.domain.models.role import Role


def auth():
    return SimpleNamespace(user=SimpleNamespace(is_superadmin=False), memberships=[], user_sub="test")


def slot(confirmed=False):
    value = PlanningSlot.create(
        district_id=uuid.uuid4(), planning_date=date(2026, 10, 11),
        planning_time=time(10), title="Termin", approval_status=(
            EventApprovalStatus.CONFIRMED if confirmed else EventApprovalStatus.PLANNED
        ),
    )
    if confirmed:
        value.released_at = datetime.now(UTC)
    return value


def body(**kw):
    data = {
        "district_id": uuid.uuid4(),
        "title": "Gemeindeabend",
        "start_at": datetime(2026, 10, 11, 20, tzinfo=UTC),
        "end_at": datetime(2026, 10, 11, 21, tzinfo=UTC),
    }
    return events.EventCreate(**(data | kw))


@pytest.mark.asyncio
async def test_create_manual_draft_with_instance_and_utc_times():
    request = body(category="Gottesdienst", description="Beschreibung")
    slots, instances = AsyncMock(), AsyncMock()
    with patch.object(events, "require_role_in_district") as permitted:
        result = await events.create_event(
            request, auth(), AsyncMock(), slot_repo=slots, inst_repo=instances
        )
    permitted.assert_called_once()
    assert permitted.call_args.args[1:] == (Role.PLANNER, request.district_id)
    saved = slots.save.await_args.args[0]
    occurrence = instances.save.await_args.args[0]
    assert saved.id == occurrence.planning_slot_id == result.id
    assert saved.approval_status == EventApprovalStatus.PLANNED
    assert saved.released_at is None
    assert saved.planning_time == time(20)
    assert result.was_released is False
    assert result.is_service and result.description == "Beschreibung"
    assert result.end_at - result.start_at == timedelta(hours=1)


@pytest.mark.asyncio
async def test_create_accepts_aware_non_utc_dates_and_district_distribution():
    congregation_id = uuid.uuid4()
    request = body(applicability=[str(congregation_id)], congregation_id=None)
    congregation_repo, slots, instances = AsyncMock(), AsyncMock(), AsyncMock()
    congregation_repo.list_by_district.return_value = [SimpleNamespace(id=congregation_id)]
    with patch.object(events, "require_role_in_district"):
        await events.create_event(
            request, auth(), AsyncMock(), slot_repo=slots,
            inst_repo=instances, cong_repo=congregation_repo,
        )
    assert slots.save.await_args.args[0].applicability == [str(congregation_id)]


@pytest.mark.asyncio
@pytest.mark.parametrize("duration", [timedelta(0), -timedelta(minutes=10)])
async def test_create_rejects_invalid_range_without_side_effects(duration):
    start = datetime(2026, 10, 11, 20, tzinfo=UTC)
    slots, instances = AsyncMock(), AsyncMock()
    with patch.object(events, "require_role_in_district"), pytest.raises(HTTPException) as exc:
        await events.create_event(body(start_at=start, end_at=start + duration),
                                  auth(), AsyncMock(), slot_repo=slots, inst_repo=instances)
    assert exc.value.status_code == 400
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_rejects_foreign_congregation_and_distribution_combination():
    foreign_id = uuid.uuid4()
    congs = AsyncMock()
    congs.get.return_value = SimpleNamespace(id=foreign_id, district_id=uuid.uuid4())
    slots, instances = AsyncMock(), AsyncMock()
    with patch.object(events, "require_role_in_district"):
        for request in (body(congregation_id=foreign_id),
                        body(congregation_id=foreign_id, applicability=["all"])):
            with pytest.raises(HTTPException) as exc:
                await events.create_event(request, auth(), AsyncMock(), slot_repo=slots,
                                          inst_repo=instances, cong_repo=congs)
            assert exc.value.status_code == 400
    slots.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_rejects_invalid_distribution():
    slots, instances = AsyncMock(), AsyncMock()
    congs = AsyncMock()
    congs.list_by_district.return_value = []
    with patch.object(events, "require_role_in_district"), pytest.raises(HTTPException) as exc:
        await events.create_event(body(applicability=[str(uuid.uuid4())]),
                                  auth(), AsyncMock(), slot_repo=slots,
                                  inst_repo=instances, cong_repo=congs)
    assert exc.value.status_code == 400
    slots.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_returns_conflict_for_duplicate_active_congregation_slot():
    request = body(congregation_id=uuid.uuid4())
    slot_repo, instance_repo, congregation_repo = AsyncMock(), AsyncMock(), AsyncMock()
    congregation_repo.get.return_value = SimpleNamespace(
        district_id=request.district_id, id=request.congregation_id,
    )
    reason = RuntimeError("unique violation")
    reason.sqlstate = "23505"
    slot_repo.save.side_effect = IntegrityError("insert", {}, reason)
    session = AsyncMock()
    with patch.object(events, "require_role_in_district"), pytest.raises(HTTPException) as exc:
        await events.create_event(
            request, auth(), session, slot_repo=slot_repo,
            inst_repo=instance_repo, cong_repo=congregation_repo,
        )
    assert exc.value.status_code == 409
    session.rollback.assert_awaited_once()
    instance_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_does_not_mask_unrelated_database_error():
    request = body()
    slot_repo = AsyncMock()
    failure = IntegrityError("insert", {}, RuntimeError("foreign key"))
    slot_repo.save.side_effect = failure
    session = AsyncMock()
    with patch.object(events, "require_role_in_district"), pytest.raises(IntegrityError):
        await events.create_event(
            request, auth(), session, slot_repo=slot_repo,
            inst_repo=AsyncMock(),
        )
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_enforces_role_before_writes():
    slots, instances = AsyncMock(), AsyncMock()
    with patch.object(events, "require_role_in_district", side_effect=HTTPException(403)):
        with pytest.raises(HTTPException) as exc:
            await events.create_event(body(), auth(), AsyncMock(),
                                      slot_repo=slots, inst_repo=instances)
    assert exc.value.status_code == 403
    slots.save.assert_not_awaited()


def test_create_schema_rejects_unknown_fields_and_blank_title():
    with pytest.raises(ValidationError):
        body(title="")
    with pytest.raises(ValidationError):
        events.EventCreate.model_validate(body().model_dump() | {"approval_status": "CONFIRMED"})


@pytest.mark.asyncio
async def test_delete_unreleased_draft():
    value = slot()
    repo = AsyncMock()
    repo.get.return_value = value
    with patch.object(events, "require_role_in_district") as permitted:
        await events.delete_event(value.id, auth(), slot_repo=repo)
    permitted.assert_called_once_with(auth(), Role.PLANNER, value.district_id)
    repo.delete.assert_awaited_once_with(value.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("published", [True, False])
async def test_delete_refuses_published_or_previously_published(published):
    value = slot(confirmed=published)
    if not published:
        value.released_at = datetime.now(UTC)
    repo = AsyncMock()
    repo.get.return_value = value
    with patch.object(events, "require_role_in_district"), pytest.raises(HTTPException) as exc:
        await events.delete_event(value.id, auth(), slot_repo=repo)
    assert exc.value.status_code == 409
    repo.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_protects_against_concurrent_release():
    value = slot()
    repo = AsyncMock()
    repo.get.return_value = value
    repo.delete.side_effect = ReleasedEventError("released")
    with patch.object(events, "require_role_in_district"), pytest.raises(HTTPException) as exc:
        await events.delete_event(value.id, auth(), slot_repo=repo)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_missing_and_permission_denied():
    repo = AsyncMock()
    repo.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await events.delete_event(uuid.uuid4(), auth(), slot_repo=repo)
    assert exc.value.status_code == 404
    repo.get.return_value = slot()
    with patch.object(events, "require_role_in_district", side_effect=HTTPException(403)):
        with pytest.raises(HTTPException) as exc:
            await events.delete_event(uuid.uuid4(), auth(), slot_repo=repo)
    assert exc.value.status_code == 403
    repo.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_rejects_unpublication_and_reactivation():
    value = slot(confirmed=True)
    repo, instances = AsyncMock(), AsyncMock()
    repo.get.return_value = value
    with patch.object(events, "require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await events.update_event(value.id, events.EventUpdate(approval_status="PLANNED"),
                                      auth(), AsyncMock(), slot_repo=repo, inst_repo=instances)
        assert exc.value.status_code == 409
        value.status = PlanningSlotStatus.CANCELLED
        with pytest.raises(HTTPException) as exc:
            await events.update_event(value.id, events.EventUpdate(status="ACTIVE"),
                                      auth(), AsyncMock(), slot_repo=repo, inst_repo=instances)
    assert exc.value.status_code == 409
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_release_cannot_reset_published_month():
    value = slot(confirmed=True)
    repo = AsyncMock()
    repo.list_for_date_range.return_value = [value]
    with patch.object(events, "require_role_in_district"), pytest.raises(HTTPException) as exc:
        await events.bulk_update_approval_status(
            events.BulkApprovalStatusRequest(year=2026, month=10, approval_status="PLANNED"),
            auth(), AsyncMock(), district_id=value.district_id, slot_repo=repo,
        )
    assert exc.value.status_code == 409
    repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_repo_sets_release_once_and_refuses_reset():
    repo_session = MagicMock()
    repo_session.get = AsyncMock(return_value=None)
    repo_session.flush = AsyncMock()
    repo = SqlPlanningSlotRepository(repo_session)
    value = slot(confirmed=True)
    await repo.save(value)
    assert value.released_at is not None
    row = repo_session.add.call_args.args[0]
    assert row.released_at == value.released_at

    repo_session.get.return_value = SimpleNamespace(
        released_at=value.released_at, approval_status=EventApprovalStatus.CONFIRMED,
        district_id=value.district_id, congregation_id=None, category=None,
        status=PlanningSlotStatus.ACTIVE,
    )
    value.approval_status = EventApprovalStatus.PLANNED
    with pytest.raises(ReleasedEventError):
        await repo.save(value)


@pytest.mark.asyncio
async def test_repo_refuses_direct_delete_after_release():
    repo_session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = SimpleNamespace(
        released_at=datetime.now(UTC), approval_status=EventApprovalStatus.CONFIRMED, generation_key=None
    )
    repo_session.execute.return_value = result
    with pytest.raises(ReleasedEventError):
        await SqlPlanningSlotRepository(repo_session).delete(uuid.uuid4())
    repo_session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_repo_deletes_draft_and_handles_missing():
    repo_session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.side_effect = [
        SimpleNamespace(released_at=None, approval_status=EventApprovalStatus.PLANNED, generation_key=None, series_id=None),
        None,
    ]
    repo_session.execute.return_value = result
    repo = SqlPlanningSlotRepository(repo_session)
    await repo.delete(uuid.uuid4())
    await repo.delete(uuid.uuid4())
    repo_session.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_deleting_generated_draft_writes_ledger_and_removes_event():
    repo_session = MagicMock()
    repo_session.execute = AsyncMock()
    repo_session.delete = AsyncMock()
    repo_session.flush = AsyncMock()
    row = SimpleNamespace(
        district_id=uuid.uuid4(),
        generation_key="draft-service:sample:2026-10-11",
        released_at=None,
        approval_status=EventApprovalStatus.PLANNED,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    repo_session.execute.return_value = result

    await SqlPlanningSlotRepository(repo_session).delete(uuid.uuid4())

    marker = repo_session.add.call_args.args[0]
    assert marker.district_id == row.district_id
    assert marker.generation_key == row.generation_key
    assert marker.deleted_at is not None
    repo_session.delete.assert_awaited_once_with(row)


@pytest.mark.asyncio
async def test_generation_suppression_is_scoped_to_matching_keys_and_district():
    repo_session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = ["key-1"]
    repo_session.execute.return_value = result
    repo = SqlPlanningSlotRepository(repo_session)

    found = await repo.list_deleted_generation_keys(
        district_id=uuid.uuid4(), generation_keys=["key-1", "key-2"]
    )
    assert found == {"key-1"}
    assert await repo.list_deleted_generation_keys(
        district_id=uuid.uuid4(), generation_keys=[]
    ) == set()
    assert repo_session.execute.await_count == 1


@pytest.mark.asyncio
async def test_repo_remembers_deleted_legacy_series_occurrence():
    from app.adapters.db.orm_models.deleted_generation_key import DeletedGenerationKeyORM
    from app.domain.models.planning_slot import planning_series_generation_key

    district_id, series_id, event_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    when = date(2026, 12, 20)
    row = SimpleNamespace(
        id=event_id, released_at=None, approval_status=EventApprovalStatus.PLANNED,
        district_id=district_id, series_id=series_id, planning_date=when,
        generation_key=None,
    )
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session.execute = AsyncMock(return_value=result)
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    await SqlPlanningSlotRepository(session).delete(event_id)

    ledger = session.add.call_args.args[0]
    assert isinstance(ledger, DeletedGenerationKeyORM)
    assert ledger.district_id == district_id
    assert ledger.generation_key == planning_series_generation_key(series_id, when)
    session.delete.assert_awaited_once_with(row)


@pytest.mark.asyncio
async def test_repository_refuses_reactivation_of_released_cancellation():
    event_slot = slot(confirmed=True)
    event_slot.status = PlanningSlotStatus.ACTIVE
    saved = SimpleNamespace(
        released_at=event_slot.released_at,
        approval_status=EventApprovalStatus.CONFIRMED,
        status=PlanningSlotStatus.CANCELLED,
        district_id=event_slot.district_id,
        congregation_id=event_slot.congregation_id,
        category=event_slot.category,
    )
    session = AsyncMock()
    session.get.return_value = saved
    with pytest.raises(ReleasedEventError):
        await SqlPlanningSlotRepository(session).save(event_slot)
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_repo_save_locks_and_refreshes_before_release_guard():
    """A stale draft must not overwrite a concurrently confirmed DB row."""
    from app.adapters.db.orm_models.planning_slot import PlanningSlotORM

    stale_draft = slot()
    current_row = SimpleNamespace(
        district_id=stale_draft.district_id,
        congregation_id=stale_draft.congregation_id,
        category=stale_draft.category,
        released_at=datetime.now(UTC),
        approval_status=EventApprovalStatus.CONFIRMED,
        status=PlanningSlotStatus.ACTIVE,
        generation_key_detached=False,
    )
    session = AsyncMock()
    session.get.return_value = current_row

    with pytest.raises(ReleasedEventError):
        await SqlPlanningSlotRepository(session).save(stale_draft)

    session.get.assert_awaited_once_with(
        PlanningSlotORM, stale_draft.id, with_for_update=True, populate_existing=True
    )
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_reassigned_series_draft_does_not_suppress_original_occurrence():
    from app.domain.models.planning_slot import planning_series_generation_key

    event = slot()
    event.series_id = uuid.uuid4()
    event.generation_key = planning_series_generation_key(event.series_id, event.planning_date)
    event.forget_generation_key_if_reassigned(
        district_id=event.district_id,
        congregation_id=uuid.uuid4(),
        category=event.category,
    )
    assert event.generation_key is None
    assert event.generation_key_detached is True

    row = SimpleNamespace(
        id=event.id, district_id=event.district_id, series_id=event.series_id,
        planning_date=event.planning_date, generation_key=None,
        generation_key_detached=event.generation_key_detached,
        released_at=None, approval_status=EventApprovalStatus.PLANNED,
    )
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    session.execute = AsyncMock(return_value=result)
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    await SqlPlanningSlotRepository(session).delete(event.id)

    session.add.assert_not_called()
    session.delete.assert_awaited_once_with(row)


def _query_result(*, row=None, invitations=()):
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    result.scalars.return_value.all.return_value = list(invitations)
    return result


@pytest.mark.asyncio
async def test_deleting_invitation_source_removes_unreleased_target_copy():
    source_id, target_id = uuid.uuid4(), uuid.uuid4()
    source = SimpleNamespace(
        id=source_id, generation_key=None, series_id=None, released_at=None,
        approval_status=EventApprovalStatus.PLANNED,
    )
    target = SimpleNamespace(
        id=target_id, generation_key=None, series_id=None, released_at=None,
        approval_status=EventApprovalStatus.PLANNED,
    )
    invitation = SimpleNamespace(
        source_planning_slot_id=source_id, source_event_id=source_id, linked_event_id=target_id,
    )
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[
        _query_result(row=source),
        _query_result(invitations=[invitation]),
        _query_result(row=target),
        _query_result(row=target),
        _query_result(),
    ])
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    await SqlPlanningSlotRepository(session).delete(source_id)

    assert {id(c.args[0]) for c in session.delete.await_args_list} == {
        id(source), id(target), id(invitation)
    }
    assert session.flush.await_count == 2


@pytest.mark.asyncio
async def test_deleting_invitation_source_cancels_released_target_copy():
    source_id, target_id = uuid.uuid4(), uuid.uuid4()
    source = SimpleNamespace(
        id=source_id, generation_key=None, series_id=None, released_at=None,
        approval_status=EventApprovalStatus.PLANNED,
    )
    target = SimpleNamespace(
        id=target_id, released_at=datetime.now(UTC),
        approval_status=EventApprovalStatus.CONFIRMED,
        status=PlanningSlotStatus.ACTIVE,
        invitation_source_event_id=source_id,
        invitation_source_congregation_id=uuid.uuid4(),
        updated_at=datetime.now(UTC),
    )
    invitation = SimpleNamespace(
        source_planning_slot_id=source_id, source_event_id=source_id, linked_event_id=target_id,
    )
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[
        _query_result(row=source),
        _query_result(invitations=[invitation]),
        _query_result(row=target),
    ])
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    await SqlPlanningSlotRepository(session).delete(source_id)

    assert target.status == PlanningSlotStatus.CANCELLED
    assert target.invitation_source_event_id is None
    assert target.invitation_source_congregation_id is None
    assert {id(c.args[0]) for c in session.delete.await_args_list} == {id(source), id(invitation)}


@pytest.mark.asyncio
async def test_deleting_linked_target_removes_invitation_but_not_source():
    target_id = uuid.uuid4()
    target = SimpleNamespace(
        id=target_id, generation_key=None, series_id=None, released_at=None,
        approval_status=EventApprovalStatus.PLANNED,
    )
    invitation = SimpleNamespace(
        source_planning_slot_id=uuid.uuid4(), source_event_id=uuid.uuid4(),
        linked_event_id=target_id,
    )
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[
        _query_result(row=target),
        _query_result(invitations=[invitation]),
    ])
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    await SqlPlanningSlotRepository(session).delete(target_id)

    assert {id(c.args[0]) for c in session.delete.await_args_list} == {id(target), id(invitation)}


@pytest.mark.asyncio
async def test_deleting_legacy_invitation_source_cleans_orphaned_link():
    source_id, target_id = uuid.uuid4(), uuid.uuid4()
    source = SimpleNamespace(
        id=source_id, generation_key=None, series_id=None, released_at=None,
        approval_status=EventApprovalStatus.PLANNED,
    )
    target = SimpleNamespace(
        id=target_id, released_at=datetime.now(UTC),
        approval_status=EventApprovalStatus.CONFIRMED,
        status=PlanningSlotStatus.ACTIVE,
        invitation_source_event_id=source_id,
        invitation_source_congregation_id=uuid.uuid4(),
        updated_at=datetime.now(UTC),
    )
    legacy_link = SimpleNamespace(
        source_planning_slot_id=None, source_event_id=source_id,
        linked_event_id=target_id,
    )
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[
        _query_result(row=source),
        _query_result(invitations=[legacy_link]),
        _query_result(row=target),
    ])
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    await SqlPlanningSlotRepository(session).delete(source_id)

    assert target.status == PlanningSlotStatus.CANCELLED
    assert {id(c.args[0]) for c in session.delete.await_args_list} == {id(source), id(legacy_link)}


def test_retention_statement_excludes_both_current_and_former_releases():
    from sqlalchemy.dialects.postgresql import dialect

    from app.application.tasks import _unreleased_retention_statement

    statement = _unreleased_retention_statement(date(2024, 10, 10))
    compiled = str(statement.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
    assert "planning_date < '2024-10-10'" in compiled
    assert "released_at IS NULL" in compiled
    assert "approval_status IS NULL" in compiled
    assert "approval_status != 'CONFIRMED'" in compiled



@pytest.mark.asyncio
@pytest.mark.parametrize("new_status", [None, EventApprovalStatus.PLANNED])
async def test_patch_stale_draft_release_race_returns_http_409(new_status):
    """The locked repository's publication error must become a client conflict."""
    event_slot = slot()
    repo, instances = AsyncMock(), AsyncMock()
    repo.get.return_value = event_slot
    repo.save.side_effect = ReleasedEventError("Freigabe zwischenzeitlich erfolgt")
    instances.get_by_planning_slot.return_value = None

    with patch.object(events, "require_role_in_district"):
        with pytest.raises(HTTPException) as exc:
            await events.update_event(
                event_slot.id,
                events.EventUpdate(approval_status=new_status),
                auth(), AsyncMock(), slot_repo=repo, inst_repo=instances,
            )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Freigabe zwischenzeitlich erfolgt"
    repo.save.assert_awaited_once_with(event_slot, require_existing=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("new_status", [
    EventApprovalStatus.PLANNED, EventApprovalStatus.CONFIRMED,
])
async def test_bulk_approval_race_returns_http_409(new_status):
    """A concurrent release/cancellation discovered during a bulk save is 409."""
    event_slot = slot()
    repo = AsyncMock()
    repo.list_for_date_range.return_value = [event_slot]
    repo.save.side_effect = ReleasedEventError("Freigabe zwischenzeitlich erfolgt")

    with patch.object(events, "require_role_in_district"), patch.object(
        events, "publish_after_commit"
    ) as publish:
        with pytest.raises(HTTPException) as exc:
            await events.bulk_update_approval_status(
                events.BulkApprovalStatusRequest(
                    year=2026, month=10, approval_status=new_status,
                ),
                auth(), AsyncMock(), district_id=event_slot.district_id, slot_repo=repo,
            )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Freigabe zwischenzeitlich erfolgt"
    repo.save.assert_awaited_once_with(event_slot, require_existing=True)
    publish.assert_not_called()



@pytest.mark.asyncio
async def test_repository_prevents_recreating_concurrently_deleted_draft():
    from app.domain.models.planning_slot import DeletedPlanningSlotError
    from app.adapters.db.orm_models.planning_slot import PlanningSlotORM

    previous_draft = slot()
    session = AsyncMock()
    session.get.return_value = None
    with pytest.raises(DeletedPlanningSlotError, match="zwischenzeitlich gelöscht"):
        await SqlPlanningSlotRepository(session).save(
            previous_draft, require_existing=True
        )
    session.get.assert_awaited_once_with(
        PlanningSlotORM, previous_draft.id, with_for_update=True, populate_existing=True
    )
    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("new_approval", [None, EventApprovalStatus.CONFIRMED])
async def test_patch_after_concurrent_delete_returns_conflict(new_approval):
    from app.domain.models.planning_slot import DeletedPlanningSlotError

    draft = slot()
    slot_repo, instances = AsyncMock(), AsyncMock()
    slot_repo.get.return_value = draft
    slot_repo.save.side_effect = DeletedPlanningSlotError("Ereignis wurde zwischenzeitlich gelöscht.")
    instances.get_by_planning_slot.return_value = None
    with patch.object(events, "require_role_in_district"), pytest.raises(HTTPException) as exc:
        await events.update_event(
            draft.id, events.EventUpdate(approval_status=new_approval),
            auth(), AsyncMock(), slot_repo=slot_repo, inst_repo=instances
        )
    assert exc.value.status_code == 409
    slot_repo.save.assert_awaited_once_with(draft, require_existing=True)


@pytest.mark.asyncio
async def test_bulk_after_concurrent_delete_returns_conflict_without_publishing():
    from app.domain.models.planning_slot import DeletedPlanningSlotError

    draft = slot()
    repo = AsyncMock()
    repo.list_for_date_range.return_value = [draft]
    repo.save.side_effect = DeletedPlanningSlotError("Ereignis wurde zwischenzeitlich gelöscht.")
    with patch.object(events, "require_role_in_district"), patch.object(
        events, "publish_after_commit"
    ) as publish, pytest.raises(HTTPException) as exc:
        await events.bulk_update_approval_status(
            events.BulkApprovalStatusRequest(
                year=2026, month=10, approval_status=EventApprovalStatus.CONFIRMED
            ),
            auth(), AsyncMock(), district_id=draft.district_id, slot_repo=repo
        )
    assert exc.value.status_code == 409
    repo.save.assert_awaited_once_with(draft, require_existing=True)
    publish.assert_not_called()
