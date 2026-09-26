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

    with (
        patch("app.adapters.api.routers.events.require_role_in_district") as require_role,
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
        patch(
            "app.adapters.api.routers.events.SqlEventInstanceRepository", return_value=instance_repo
        ),
        patch(
            "app.adapters.api.routers.events.SqlCongregationRepository",
            return_value=congregation_repo,
        ),
    ):
        result = await events.list_events(
            _auth(),
            AsyncMock(),
            district_id=district_id,
            congregation_id=None,
            group_id=group_id,
            only_district_level=False,
            status_filter=PlanningSlotStatus.ACTIVE,
            approval_status=EventApprovalStatus.PLANNED,
            from_dt=None,
            to_dt=None,
            limit=1,
            offset=0,
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
    visible = _slot(district_id=district_id, applicability=["all"])
    invisible = _slot(district_id=district_id, applicability=[])
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = [visible, invisible]
    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = []

    with (
        patch("app.adapters.api.routers.events.require_role_in_district"),
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
        patch(
            "app.adapters.api.routers.events.SqlEventInstanceRepository", return_value=instance_repo
        ),
    ):
        result = await events.list_events(
            _auth(),
            AsyncMock(),
            district_id=district_id,
            congregation_id=congregation_id,
            group_id=None,
            only_district_level=False,
            status_filter=None,
            approval_status=None,
            from_dt=None,
            to_dt=None,
            limit=50,
            offset=0,
        )

    assert [item.id for item in result.items] == [visible.id]


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
    with (
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
        patch(
            "app.adapters.api.routers.events.SqlEventInstanceRepository", return_value=instance_repo
        ),
    ):
        result = await events.list_events(
            _auth(is_superadmin=True),
            AsyncMock(),
            district_id=None,
            congregation_id=None,
            group_id=None,
            only_district_level=False,
            status_filter=None,
            approval_status=None,
            from_dt=None,
            to_dt=None,
            limit=50,
            offset=0,
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

    with (
        patch("app.adapters.api.routers.events.require_role_in_district"),
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
        patch(
            "app.adapters.api.routers.events.SqlEventInstanceRepository", return_value=instance_repo
        ),
    ):
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

    with (
        patch("app.adapters.api.routers.events.require_role_in_district"),
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
        patch(
            "app.adapters.api.routers.events.SqlEventInstanceRepository", return_value=instance_repo
        ),
    ):
        await events.update_event(
            slot.id,
            events.EventUpdate(congregation_id=None, description=None),
            _auth(),
            AsyncMock(),
        )

    assert slot.congregation_id is None
    assert instance.description is None
    instance_repo.save.assert_awaited_once_with(instance)


@pytest.mark.asyncio
async def test_update_event_rejects_missing_slot() -> None:
    slot_repo = AsyncMock()
    slot_repo.get.return_value = None
    with patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo):
        with pytest.raises(HTTPException) as error:
            await events.update_event(uuid.uuid4(), events.EventUpdate(), _auth(), AsyncMock())

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
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
        patch(
            "app.adapters.api.routers.events.SqlEventInstanceRepository", return_value=instance_repo
        ),
        patch(
            "app.adapters.api.routers.events.SqlCongregationRepository",
            return_value=congregation_repo,
        ),
    ):
        with pytest.raises(HTTPException) as error:
            await events.update_event(
                slot.id,
                events.EventUpdate(congregation_id=foreign_congregation.id),
                _auth(),
                AsyncMock(),
            )

    assert error.value.status_code == 400
    slot_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_event_rejects_end_time_without_instance_and_invalid_range() -> None:
    slot = _slot()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = None

    with (
        patch("app.adapters.api.routers.events.require_role_in_district"),
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
        patch(
            "app.adapters.api.routers.events.SqlEventInstanceRepository", return_value=instance_repo
        ),
    ):
        with pytest.raises(HTTPException) as no_instance_error:
            await events.update_event(
                slot.id,
                events.EventUpdate(end_at=datetime(2026, 9, 26, 12, tzinfo=UTC)),
                _auth(),
                AsyncMock(),
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
            )

    assert no_instance_error.value.status_code == 400
    assert range_error.value.status_code == 400


@pytest.mark.asyncio
async def test_update_event_rejects_description_without_instance() -> None:
    slot = _slot()
    slot_repo = AsyncMock()
    slot_repo.get.return_value = slot
    instance_repo = AsyncMock()
    instance_repo.get_by_planning_slot.return_value = None
    with (
        patch("app.adapters.api.routers.events.require_role_in_district"),
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
        patch(
            "app.adapters.api.routers.events.SqlEventInstanceRepository", return_value=instance_repo
        ),
    ):
        with pytest.raises(HTTPException) as error:
            await events.update_event(
                slot.id, events.EventUpdate(description="Text"), _auth(), AsyncMock()
            )

    assert error.value.status_code == 400
    slot_repo.save.assert_not_awaited()


def test_event_update_rejects_unknown_fields_and_empty_title() -> None:
    with pytest.raises(ValidationError):
        events.EventUpdate.model_validate({"district_id": str(uuid.uuid4())})
    with pytest.raises(ValidationError):
        events.EventUpdate.model_validate({"title": ""})


@pytest.mark.asyncio
async def test_bulk_approval_status_updates_month_slots() -> None:
    district_id = uuid.uuid4()
    slot = _slot(district_id=district_id)
    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = [slot]
    request = events.BulkApprovalStatusRequest(
        year=2026, month=12, approval_status=EventApprovalStatus.CONFIRMED
    )

    with (
        patch("app.adapters.api.routers.events.require_role_in_district"),
        patch("app.adapters.api.routers.events.SqlPlanningSlotRepository", return_value=slot_repo),
    ):
        result = await events.bulk_update_approval_status(
            request, _auth(), AsyncMock(), district_id=district_id
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
