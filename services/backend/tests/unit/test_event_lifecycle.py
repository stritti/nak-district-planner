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
