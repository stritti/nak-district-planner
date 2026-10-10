# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.routers import events
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
)
from app.domain.models.role import Role
from app.domain.ports.calendar import CalendarConnectorError


@pytest.fixture(autouse=True)
def _no_responsible_lookup():
    """Handlers are called directly here; responsible loading is tested separately."""
    with patch.object(events, "_load_responsible", AsyncMock(return_value={})):
        yield


def _auth(*, is_superadmin: bool = False):
    user = SimpleNamespace(is_superadmin=is_superadmin)
    return SimpleNamespace(user=user, memberships=[], user_sub="test-user")


def _slot(
    *,
    district_id: uuid.UUID | None = None,
    congregation_id: uuid.UUID | None = None,
    status: PlanningSlotStatus = PlanningSlotStatus.ACTIVE,
    approval_status: EventApprovalStatus | None = EventApprovalStatus.PLANNED,
    applicability: list[str] | None = None,
) -> PlanningSlot:
    return PlanningSlot.create(
        district_id=district_id or uuid.uuid4(),
        planning_date=date(2026, 9, 26),
        planning_time=time(10),
        congregation_id=congregation_id,
        title="Gottesdienst",
        category="Gottesdienst",
        status=status,
        approval_status=approval_status,
        applicability=applicability,
    )


def _instance(slot: PlanningSlot) -> EventInstance:
    return EventInstance.create(
        planning_slot_id=slot.id,
        title="Gottesdienst",
        description="Bisherige Beschreibung",
        actual_start_at=datetime(2026, 9, 26, 10, tzinfo=UTC),
        actual_end_at=datetime(2026, 9, 26, 11, tzinfo=UTC),
        source=EventSource.INTERNAL,
        visibility=EventVisibility.PUBLIC,
    )


@pytest.mark.asyncio
async def test_resolve_deviation_restores_planned_duration():
    from app.domain.models.event_instance import SyncState
    slot = _slot()
    instance = _instance(slot)
    instance.actual_start_at += timedelta(hours=2)
    instance.actual_end_at += timedelta(hours=2)
    instance.deviation_flag = True
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get.return_value = instance
    instance_repo.get_by_planning_slot.return_value = instance
    with patch.object(events, "require_role_in_district") as require_role:
        result = await events.resolve_event_deviation(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    require_role.assert_called_once_with(_auth(), Role.PLANNER, slot.district_id)
    assert result.start_at == datetime(2026, 9, 26, 10, tzinfo=UTC)
    assert result.end_at - result.start_at == timedelta(minutes=90)
    assert instance.sync_state == SyncState.DIRTY_INTERNAL
    assert not instance.deviation_flag


@pytest.mark.asyncio
async def test_resolve_deviation_reports_no_active_deviation():
    slot = _slot()
    instance = _instance(slot)
    instance.deviation_flag = False
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get.return_value = instance
    instance_repo.get_by_planning_slot.return_value = instance
    with (
        patch.object(events, "require_role_in_district"),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_deviation(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 409
    instance_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_deviation_reports_provider_failure_and_remains_retryable():
    from app.domain.models.event_instance import SyncState

    slot = _slot()
    instance = _instance(slot)
    instance.calendar_integration_id = uuid.uuid4()
    instance.actual_start_at += timedelta(hours=1)
    instance.actual_end_at += timedelta(hours=1)
    instance.deviation_flag = True
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get.return_value = instance
    instance_repo.get_by_planning_slot.return_value = instance
    push = AsyncMock(side_effect=CalendarConnectorError("provider down"))
    with (
        patch.object(events, "SqlPlanningSlotRepository", return_value=slot_repo),
        patch.object(events, "SqlEventInstanceRepository", return_value=instance_repo),
        patch.object(events, "require_role_in_district"),
        patch.object(events, "push_deviation_resolution", push),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_deviation(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )

    assert exc.value.status_code == 502
    assert instance.deviation_flag is True
    assert instance.sync_state == SyncState.DIRTY_INTERNAL


@pytest.mark.asyncio
async def test_resolve_deviation_pushes_linked_instance():
    slot = _slot()
    instance = _instance(slot)
    instance.calendar_integration_id = uuid.uuid4()
    instance.actual_start_at += timedelta(hours=1)
    instance.actual_end_at += timedelta(hours=1)
    instance.deviation_flag = True
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get.return_value = instance
    instance_repo.get_by_planning_slot.return_value = instance
    push = AsyncMock(return_value=True)
    with (
        patch.object(events, "require_role_in_district"),
        patch.object(events, "push_deviation_resolution", push),
    ):
        await events.resolve_event_deviation(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )

    push.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_slot", [True, False])
async def test_resolve_deviation_missing_entities(missing_slot):
    slot = _slot()
    slot_repo, instance_repo = AsyncMock(), AsyncMock()
    slot_repo.get.return_value = None if missing_slot else slot
    instance_repo.get_by_planning_slot.return_value = None
    with (
        patch.object(events, "require_role_in_district"),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_deviation(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_deviation_enforces_district_permission():
    slot = _slot()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    with (
        patch.object(events, "require_role_in_district", side_effect=HTTPException(403)),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_deviation(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 403
    instance_repo.get_by_planning_slot.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_events_applies_filters_and_paginates() -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    group_id = uuid.uuid4()
    matching = _slot(district_id=district_id, congregation_id=congregation_id)
    wrong_group = _slot(district_id=district_id, congregation_id=uuid.uuid4())
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = [matching, wrong_group]
    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = []
    congregation_repo = AsyncMock()
    congregation_repo.list_by_district.return_value = [
        SimpleNamespace(id=congregation_id, group_id=group_id)
    ]

    with patch(
        "app.adapters.api.routers.events.require_role_in_district"
    ) as require_role:
        result = await events.list_events(
            _auth(),
            AsyncMock(),
            district_id=district_id,
            congregation_id=None,
            group_id=group_id,
            only_district_level=False,
            status_filter=PlanningSlotStatus.ACTIVE,
            approval_status=EventApprovalStatus.PLANNED,
            is_service=None,
            from_dt=None,
            to_dt=None,
            limit=1,
            offset=0,
            slot_repo=slot_repo,
            cong_repo=congregation_repo,
            inst_repo=instance_repo,
        )

    require_role.assert_called_once_with(_auth(), Role.VIEWER, district_id)
    assert result.total == 1
    assert result.items[0].id == matching.id
    assert result.limit == 1
    assert result.offset == 0
    congregation_repo.list_by_district.assert_awaited_once_with(district_id)


@pytest.mark.asyncio
async def test_list_events_filters_district_slots_by_applicability() -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    visible = _slot(
        district_id=district_id,
        applicability=["all"],
        approval_status=EventApprovalStatus.CONFIRMED,
    )
    invisible = _slot(
        district_id=district_id, applicability=[], approval_status=EventApprovalStatus.CONFIRMED
    )
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = [visible, invisible]
    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = []

    with patch("app.adapters.api.routers.events.require_role_in_district"):
        result = await events.list_events(
            _auth(),
            AsyncMock(),
            district_id=district_id,
            congregation_id=congregation_id,
            group_id=None,
            only_district_level=False,
            status_filter=None,
            approval_status=None,
            is_service=None,
            from_dt=None,
            to_dt=None,
            limit=50,
            offset=0,
            slot_repo=slot_repo,
            inst_repo=instance_repo,
        )

    assert [item.id for item in result.items] == [visible.id]


@pytest.mark.asyncio
async def test_list_events_marks_and_filters_service_events() -> None:
    district_id = uuid.uuid4()
    service = _slot(district_id=district_id)
    other = PlanningSlot.create(
        district_id=district_id,
        planning_date=date(2026, 9, 27),
        planning_time=time(10),
        title="Andacht",
        category="Andacht",
    )
    uncategorised = PlanningSlot.create(
        district_id=district_id,
        planning_date=date(2026, 9, 28),
        planning_time=time(10),
        title="Ohne Kategorie",
        category=None,
    )
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = [service, other, uncategorised]
    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = []

    async def call(is_service: bool | None):
        with patch("app.adapters.api.routers.events.require_role_in_district"):
            return await events.list_events(
                _auth(),
                AsyncMock(),
                district_id=district_id,
                congregation_id=None,
                group_id=None,
                only_district_level=False,
                status_filter=None,
                approval_status=None,
                is_service=is_service,
                from_dt=None,
                to_dt=None,
                limit=50,
                offset=0,
                slot_repo=slot_repo,
                inst_repo=instance_repo,
            )

    all_result = await call(None)
    assert [item.id for item in all_result.items] == [service.id, other.id, uncategorised.id]
    assert [item.is_service for item in all_result.items] == [True, False, False]

    service_only = await call(True)
    assert [item.id for item in service_only.items] == [service.id]
    assert service_only.total == 1

    other_only = await call(False)
    assert [item.id for item in other_only.items] == [other.id, uncategorised.id]
    assert other_only.total == 2


@pytest.mark.asyncio
async def test_list_events_accepts_datetime_range_filters() -> None:
    district_id = uuid.uuid4()
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = []
    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = []
    with patch("app.adapters.api.routers.events.require_role_in_district"):
        await events.list_events(
            _auth(),
            AsyncMock(),
            district_id=district_id,
            congregation_id=None,
            group_id=None,
            only_district_level=False,
            status_filter=None,
            approval_status=None,
            is_service=None,
            from_dt=datetime(2026, 9, 26, 22, 0, tzinfo=UTC),
            to_dt=datetime(2026, 10, 3, 21, 59, 59, tzinfo=UTC),
            limit=50,
            offset=0,
            slot_repo=slot_repo,
            inst_repo=instance_repo,
        )

    kwargs = slot_repo.list_for_date_range.await_args.kwargs
    assert kwargs["from_date"] == date(2026, 9, 26)
    assert kwargs["to_date"] == date(2026, 10, 3)


@pytest.mark.asyncio
async def test_list_events_requires_district_for_non_superadmin() -> None:
    with pytest.raises(HTTPException) as error:
        await events.list_events(_auth(), AsyncMock())

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_list_events_allows_superadmin_without_district() -> None:
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = []
    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = []
    result = await events.list_events(
        _auth(is_superadmin=True),
        AsyncMock(),
        district_id=None,
        congregation_id=None,
        group_id=None,
        only_district_level=False,
        status_filter=None,
        approval_status=None,
        is_service=None,
        from_dt=None,
        to_dt=None,
        limit=50,
        offset=0,
        slot_repo=slot_repo,
        inst_repo=instance_repo,
    )

    assert result.items == []
    assert slot_repo.list_for_date_range.await_args.kwargs["district_id"] == uuid.UUID(int=0)


@pytest.mark.asyncio
async def test_update_event_persists_instance_and_slot_changes() -> None:
    slot = _slot(congregation_id=uuid.uuid4())
    instance = _instance(slot)
    new_start = datetime(2026, 10, 1, 18, tzinfo=UTC)
    new_end = new_start + timedelta(hours=2)
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = instance

    with patch("app.adapters.api.routers.events.require_role_in_district"):
        result = await events.update_event(
            slot.id,
            events.EventUpdate(
                title="Neuer Titel",
                description="Neue Beschreibung",
                category="Andacht",
                status=PlanningSlotStatus.CANCELLED,
                start_at=new_start,
                end_at=new_end,
            ),
            _auth(),
            AsyncMock(),
            slot_repo=slot_repo,
            inst_repo=instance_repo,
        )

    assert result.title == "Neuer Titel"
    assert result.description == "Neue Beschreibung"
    assert result.start_at == new_start
    assert result.end_at == new_end
    assert result.status == PlanningSlotStatus.CANCELLED
    assert slot.planning_date == new_start.date()
    assert slot.planning_time == new_start.timetz()
    slot_repo.save.assert_awaited_once_with(slot)
    instance_repo.save.assert_awaited_once_with(instance)


@pytest.mark.asyncio
async def test_update_event_can_clear_congregation_and_description() -> None:
    slot = _slot(congregation_id=uuid.uuid4())
    instance = _instance(slot)
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = instance

    with patch("app.adapters.api.routers.events.require_role_in_district"):
        await events.update_event(
            slot.id,
            events.EventUpdate(congregation_id=None, description=None),
            _auth(),
            AsyncMock(),
            slot_repo=slot_repo,
            inst_repo=instance_repo,
        )

    assert slot.congregation_id is None
    assert instance.description is None
    instance_repo.save.assert_awaited_once_with(instance)


@pytest.mark.asyncio
async def test_update_event_rejects_missing_slot() -> None:
    slot_repo = AsyncMock()
    slot_repo.get.return_value = None
    with pytest.raises(HTTPException) as error:
        await events.update_event(
            uuid.uuid4(),
            events.EventUpdate(),
            _auth(),
            AsyncMock(),
            slot_repo=slot_repo,
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_update_event_rejects_congregation_from_another_district() -> None:
    slot = _slot()
    foreign_congregation = SimpleNamespace(id=uuid.uuid4(), district_id=uuid.uuid4())
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = None
    congregation_repo = AsyncMock()
    congregation_repo.get.return_value = foreign_congregation

    with (
        patch("app.adapters.api.routers.events.require_role_in_district"),
        pytest.raises(HTTPException) as error,
    ):
        await events.update_event(
            slot.id,
            events.EventUpdate(congregation_id=foreign_congregation.id),
            _auth(),
            AsyncMock(),
            slot_repo=slot_repo,
            cong_repo=congregation_repo,
            inst_repo=instance_repo,
        )

    assert error.value.status_code == 400
    slot_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_event_moves_slot_without_instance_and_rejects_invalid_range() -> None:
    slot = _slot()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = None
    new_start = datetime(2026, 10, 1, 8, 30, tzinfo=UTC)
    new_end = new_start + timedelta(hours=1)
    with patch("app.adapters.api.routers.events.require_role_in_district"):
        result = await events.update_event(
            slot.id,
            events.EventUpdate(start_at=new_start, end_at=new_end),
            _auth(),
            AsyncMock(),
            slot_repo=slot_repo,
            inst_repo=instance_repo,
        )
        with pytest.raises(HTTPException) as range_error:
            await events.update_event(
                slot.id,
                events.EventUpdate(
                    start_at=datetime(2026, 9, 26, 12, tzinfo=UTC),
                    end_at=datetime(2026, 9, 26, 11, tzinfo=UTC),
                ),
                _auth(),
                AsyncMock(),
                slot_repo=slot_repo,
                inst_repo=instance_repo,
            )

    assert range_error.value.status_code == 400
    assert result.start_at == new_start
    assert slot.planning_date == new_start.date()
    assert slot.planning_time == new_start.timetz()
    assert result.end_at == new_start  # duration not representable without instance
    slot_repo.save.assert_awaited_once_with(slot)
    instance_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_event_rejects_description_without_instance() -> None:
    slot = _slot()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = None
    with (
        patch("app.adapters.api.routers.events.require_role_in_district"),
        pytest.raises(HTTPException) as error,
    ):
        await events.update_event(
            slot.id,
            events.EventUpdate(description="Text"),
            _auth(),
            AsyncMock(),
            slot_repo=slot_repo,
            inst_repo=instance_repo,
        )

    assert error.value.status_code == 400
    slot_repo.save.assert_not_awaited()


def test_event_update_rejects_unknown_fields_and_empty_title() -> None:
    with pytest.raises(ValidationError):
        events.EventUpdate.model_validate({"district_id": str(uuid.uuid4())})
    with pytest.raises(ValidationError):
        events.EventUpdate.model_validate({"title": ""})


async def _patch_event(slot: PlanningSlot, body: events.EventUpdate, congregations: list):
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = None
    congregation_repo = AsyncMock()
    congregation_repo.list_by_district.return_value = congregations
    with patch("app.adapters.api.routers.events.require_role_in_district"):
        result = await events.update_event(
            slot.id,
            body,
            _auth(),
            AsyncMock(),
            slot_repo=slot_repo,
            cong_repo=congregation_repo,
            inst_repo=instance_repo,
        )
    return result, slot_repo, congregation_repo


@pytest.mark.asyncio
async def test_update_event_distributes_district_event_to_congregations() -> None:
    slot = _slot()
    congregations = [SimpleNamespace(id=uuid.uuid4()), SimpleNamespace(id=uuid.uuid4())]
    body = events.EventUpdate(applicability=[str(c.id) for c in congregations])

    result, slot_repo, congregation_repo = await _patch_event(slot, body, congregations)

    assert result.applicability == [str(c.id) for c in congregations]
    congregation_repo.list_by_district.assert_awaited_once_with(slot.district_id)
    slot_repo.save.assert_awaited_once_with(slot)


@pytest.mark.asyncio
async def test_update_event_null_applicability_clears_distribution() -> None:
    slot = _slot(applicability=["all"])

    result, _, _ = await _patch_event(slot, events.EventUpdate(applicability=None), [])

    assert result.applicability == []


@pytest.mark.asyncio
async def test_update_event_rejects_foreign_congregation_in_applicability() -> None:
    slot = _slot(applicability=["all"])

    with pytest.raises(HTTPException) as error:
        await _patch_event(
            slot, events.EventUpdate(applicability=[str(uuid.uuid4())]), [SimpleNamespace(id=uuid.uuid4())]
        )

    assert error.value.status_code == 400
    assert "Bezirk" in error.value.detail
    assert slot.applicability == ["all"]


@pytest.mark.asyncio
async def test_update_event_moving_to_congregation_drops_distribution() -> None:
    slot = _slot(applicability=["all"])
    congregation = SimpleNamespace(id=uuid.uuid4(), district_id=slot.district_id)
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = None
    congregation_repo = AsyncMock()
    congregation_repo.get.return_value = congregation

    with patch("app.adapters.api.routers.events.require_role_in_district"):
        result = await events.update_event(
            slot.id,
            events.EventUpdate(congregation_id=congregation.id),
            _auth(),
            AsyncMock(),
            slot_repo=slot_repo,
            cong_repo=congregation_repo,
            inst_repo=instance_repo,
        )

    assert result.congregation_id == congregation.id
    assert result.applicability == []


@pytest.mark.parametrize(
    "applicability",
    [[""], ["x" * 65], ["all"] * 501],
    ids=["blank-entry", "overlong-entry", "too-many-entries"],
)
def test_event_update_bounds_applicability_input(applicability) -> None:
    with pytest.raises(ValidationError):
        events.EventUpdate.model_validate({"applicability": applicability})


@pytest.mark.asyncio
async def test_bulk_approval_status_updates_month_slots() -> None:
    district_id = uuid.uuid4()
    slot = _slot(district_id=district_id)
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = [slot]
    request = events.BulkApprovalStatusRequest(
        year=2026, month=12, approval_status=EventApprovalStatus.CONFIRMED
    )

    with patch("app.adapters.api.routers.events.require_role_in_district"):
        result = await events.bulk_update_approval_status(
            request,
            _auth(),
            AsyncMock(),
            district_id=district_id,
            slot_repo=slot_repo,
        )

    assert result.updated_count == 1
    assert slot.approval_status == EventApprovalStatus.CONFIRMED
    start, end = (
        slot_repo.list_for_date_range.await_args.kwargs["from_date"],
        slot_repo.list_for_date_range.await_args.kwargs["to_date"],
    )
    assert (start, end) == (date(2026, 12, 1), date(2026, 12, 31))
    slot_repo.save.assert_awaited_once_with(slot)


@pytest.mark.asyncio
async def test_bulk_approval_status_requires_district_for_non_superadmin() -> None:
    request = events.BulkApprovalStatusRequest(
        year=2026, month=9, approval_status=EventApprovalStatus.CONFIRMED
    )
    with pytest.raises(HTTPException) as error:
        await events.bulk_update_approval_status(request, _auth(), AsyncMock(), district_id=None)

    assert error.value.status_code == 403


def test_bulk_approval_status_rejects_invalid_month_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        events.BulkApprovalStatusRequest(
            year=2026, month=13, approval_status=EventApprovalStatus.CONFIRMED
        )
    with pytest.raises(ValidationError):
        events.BulkApprovalStatusRequest.model_validate(
            {"year": 2026, "month": 9, "approval_status": "CONFIRMED", "unused": True}
        )


@pytest.mark.asyncio
async def test_resolve_conflict_routes_through_state_machine_and_pushes() -> None:
    from app.domain.models.event_instance import SyncState

    slot = _slot()
    instance = _instance(slot)
    instance.calendar_integration_id = uuid.uuid4()
    instance.sync_state = SyncState.CONFLICT
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = instance
    instance_repo.get.return_value = instance
    push = AsyncMock(return_value=True)
    with (
        patch.object(events, "require_role_in_district") as require_role,
        patch.object(events, "push_conflict_resolution", push),
    ):
        result = await events.resolve_event_conflict(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    require_role.assert_called_once_with(_auth(), Role.PLANNER, slot.district_id)
    push.assert_awaited_once()
    assert result.sync_state == SyncState.DIRTY_INTERNAL
    instance_repo.save.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_conflict_without_active_conflict_is_rejected() -> None:
    from app.domain.models.event_instance import SyncState

    slot = _slot()
    instance = _instance(slot)
    instance.sync_state = SyncState.DIRTY_EXTERNAL
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = instance
    with (
        patch.object(events, "require_role_in_district"),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_conflict(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 409
    assert instance.sync_state == SyncState.DIRTY_EXTERNAL


@pytest.mark.asyncio
async def test_resolve_conflict_provider_failure_restores_conflict() -> None:
    from app.domain.models.event_instance import SyncState

    slot = _slot()
    instance = _instance(slot)
    instance.calendar_integration_id = uuid.uuid4()
    instance.sync_state = SyncState.CONFLICT
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = instance
    push = AsyncMock(side_effect=CalendarConnectorError("provider down"))
    with (
        patch.object(events, "require_role_in_district"),
        patch.object(events, "push_conflict_resolution", push),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_conflict(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 502
    assert instance.sync_state == SyncState.CONFLICT


@pytest.mark.asyncio
async def test_resolve_conflict_missing_entities() -> None:
    slot_repo, instance_repo = AsyncMock(), AsyncMock()
    slot_repo.get.return_value = None
    with (
        patch.object(events, "require_role_in_district"),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_conflict(
            uuid.uuid4(), _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 404


def test_resolve_conflict_policy_transition_only_from_conflict() -> None:
    from app.domain.models.event_instance import SyncState
    from app.domain.services.sync_policy import resolve_conflict

    assert resolve_conflict(SyncState.CONFLICT) == SyncState.DIRTY_INTERNAL
    for state in (SyncState.CLEAN, SyncState.DIRTY_INTERNAL, SyncState.DIRTY_EXTERNAL):
        with pytest.raises(ValueError):
            resolve_conflict(state)


@pytest.mark.asyncio
async def test_imported_holiday_distributed_to_congregation_appears_in_its_view() -> None:
    """Imported holidays are reference data and stay visible once referenced (#466)."""
    from app.application.feiertage_service import (
        import_kirchliche_festtage,
        reference_feiertage_for_congregation,
    )

    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    saved: list[PlanningSlot] = []
    import_repo = AsyncMock()
    import_repo.list_for_date_range.return_value = []
    import_repo.save.side_effect = saved.append
    with patch(
        "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=import_repo
    ):
        await import_kirchliche_festtage(district_id, 2026, AsyncMock())
        import_repo.list_for_date_range.return_value = saved
        await reference_feiertage_for_congregation(district_id, congregation_id, AsyncMock())

    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = saved
    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = []
    with patch("app.adapters.api.routers.events.require_role_in_district"):
        result = await events.list_events(
            _auth(),
            AsyncMock(),
            district_id=district_id,
            congregation_id=congregation_id,
            group_id=None,
            only_district_level=False,
            status_filter=None,
            approval_status=None,
            is_service=None,
            from_dt=datetime(2026, 1, 1, tzinfo=UTC),
            to_dt=datetime(2026, 12, 31, tzinfo=UTC),
            limit=500,
            offset=0,
            slot_repo=slot_repo,
            inst_repo=instance_repo,
        )

    assert saved
    assert {item.id for item in result.items} == {slot.id for slot in saved}


# ── v1.0 provider scope (#467): unsupported provider on outbound write → 409 ─


@pytest.mark.asyncio
async def test_resolve_deviation_with_unsupported_provider_returns_409():
    from app.domain.errors import UnsupportedCalendarTypeError
    from app.domain.models.event_instance import SyncState

    slot = _slot()
    instance = _instance(slot)
    instance.calendar_integration_id = uuid.uuid4()
    instance.deviation_flag = True
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get.return_value = instance
    instance_repo.get_by_planning_slot.return_value = instance
    push = AsyncMock(side_effect=UnsupportedCalendarTypeError("GOOGLE"))
    with (
        patch.object(events, "SqlPlanningSlotRepository", return_value=slot_repo),
        patch.object(events, "SqlEventInstanceRepository", return_value=instance_repo),
        patch.object(events, "require_role_in_district"),
        patch.object(events, "push_deviation_resolution", push),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_deviation(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )

    assert exc.value.status_code == 409
    assert "ICS" in exc.value.detail
    assert instance.deviation_flag is True
    assert instance.sync_state == SyncState.DIRTY_INTERNAL


@pytest.mark.asyncio
async def test_resolve_conflict_with_unsupported_provider_returns_409() -> None:
    from app.domain.errors import UnsupportedCalendarTypeError
    from app.domain.models.event_instance import SyncState

    slot = _slot()
    instance = _instance(slot)
    instance.calendar_integration_id = uuid.uuid4()
    instance.sync_state = SyncState.CONFLICT
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = instance
    push = AsyncMock(side_effect=UnsupportedCalendarTypeError("MICROSOFT"))
    with (
        patch.object(events, "require_role_in_district"),
        patch.object(events, "push_conflict_resolution", push),
        pytest.raises(HTTPException) as exc,
    ):
        await events.resolve_event_conflict(
            slot.id, _auth(), AsyncMock(), slot_repo=slot_repo, instance_repo=instance_repo
        )
    assert exc.value.status_code == 409
    assert "ICS" in exc.value.detail
    assert instance.sync_state == SyncState.CONFLICT
