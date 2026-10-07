from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers.service_assignments import _raise_blocking_conflicts
from app.adapters.api.schemas.conflict import ConflictResponse
from app.application.service_assignment_conflict import check_service_assignment_conflicts
from app.config import Settings
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.leader import Leader
from app.domain.models.planning_slot import PlanningSlot
from app.domain.planning.conflict_result import ConflictResult, ScheduledService, Severity


def _conflict(severity: Severity) -> ConflictResult:
    return ConflictResult(
        rule_id="test_rule",
        severity=severity,
        message="Konflikt",
    )


def test_blocking_conflict_returns_http_409() -> None:
    with pytest.raises(HTTPException) as exc:
        _raise_blocking_conflicts([_conflict(Severity.BLOCK)], confirm_warnings=False)

    assert exc.value.status_code == 409


def test_warning_requires_explicit_confirmation() -> None:
    with pytest.raises(HTTPException) as exc:
        _raise_blocking_conflicts([_conflict(Severity.WARN)], confirm_warnings=False)

    assert exc.value.status_code == 409


def test_confirmed_warning_is_allowed() -> None:
    _raise_blocking_conflicts([_conflict(Severity.WARN)], confirm_warnings=True)


def test_conflict_response_schema_serializes_stable_error_shape() -> None:
    response = ConflictResponse(
        conflicts=[
            {
                "rule_id": "test_rule",
                "severity": Severity.BLOCK,
                "message": "Konflikt",
                "details": {},
            }
        ]
    )

    assert response.model_dump(mode="json") == {
        "conflicts": [
            {
                "rule_id": "test_rule",
                "severity": "BLOCK",
                "message": "Konflikt",
                "details": {},
            }
        ]
    }


@pytest.mark.asyncio
async def test_conflict_adapter_returns_no_conflicts_without_planning_slot() -> None:
    """Without a slot there is nothing to compare; the router already answered 404."""
    session = AsyncMock()
    with patch("app.application.service_assignment_conflict.SqlPlanningSlotRepository") as slot_cls:
        slot_cls.return_value.get = AsyncMock(return_value=None)

        result = await check_service_assignment_conflicts(
            session,
            event_id=uuid.uuid4(),
            leader_id=uuid.uuid4(),
        )

    assert result == []


@pytest.mark.asyncio
async def test_conflict_adapter_skips_checks_when_disabled() -> None:
    session = AsyncMock()
    with patch(
        "app.application.service_assignment_conflict.settings.conflict_check_enabled", False
    ):
        result = await check_service_assignment_conflicts(
            session,
            event_id=uuid.uuid4(),
            leader_id=uuid.uuid4(),
        )

    assert result == []
    session.execute.assert_not_awaited()


def test_conflict_settings_have_safe_defaults_and_validate_travel_minutes() -> None:
    settings = Settings()

    assert settings.conflict_check_enabled is True
    assert settings.min_travel_minutes == 30
    with pytest.raises(ValueError):
        Settings(min_travel_minutes=-1)


_PATCH = "app.application.service_assignment_conflict."
_START = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)


def _slot(slot_id: uuid.UUID | None = None, *, start: datetime = _START) -> PlanningSlot:
    return PlanningSlot.create(
        district_id=uuid.uuid4(),
        planning_date=start.date(),
        planning_time=start.time().replace(tzinfo=None),
        congregation_id=uuid.uuid4(),
        slot_id=slot_id,
    )


async def _check(
    *,
    target_slot: PlanningSlot,
    target_instance: EventInstance | None,
    schedule: list[ScheduledService],
    leader: Leader | None,
    exclude_assignment_id: uuid.UUID | None = None,
):
    session = AsyncMock()
    with (
        patch(_PATCH + "SqlPlanningSlotRepository") as slot_cls,
        patch(_PATCH + "SqlEventInstanceRepository") as instance_cls,
        patch(_PATCH + "SqlServiceAssignmentRepository") as assignment_cls,
        patch(_PATCH + "SqlLeaderRepository") as leader_cls,
        patch(_PATCH + "SqlLeaderUnavailabilityRepository") as absence_cls,
    ):
        slot_cls.return_value.get = AsyncMock(return_value=target_slot)
        instance_cls.return_value.get_by_planning_slot = AsyncMock(return_value=target_instance)
        schedule_query = AsyncMock(return_value=schedule)
        assignment_cls.return_value.list_leader_schedule = schedule_query
        assignment_cls.return_value.list_by_leader = AsyncMock(
            side_effect=AssertionError("N+1: must not load the leader's whole history")
        )
        leader_cls.return_value.get = AsyncMock(return_value=leader)
        absence_cls.return_value.list_overlapping = AsyncMock(return_value=[])

        result = await check_service_assignment_conflicts(
            session,
            event_id=target_slot.id,
            leader_id=uuid.uuid4(),
            exclude_assignment_id=exclude_assignment_id,
        )
    return result, schedule_query


def _instance(slot: PlanningSlot, start: datetime, end: datetime) -> EventInstance:
    return EventInstance.create(
        planning_slot_id=slot.id,
        title="Gottesdienst",
        actual_start_at=start,
        actual_end_at=end,
        source=EventSource.INTERNAL,
        visibility=EventVisibility.PUBLIC,
    )


@pytest.mark.asyncio
async def test_conflict_adapter_builds_context_from_one_windowed_query() -> None:
    target = _slot()
    existing = ScheduledService(
        congregation_id=uuid.uuid4(),
        planning_date=_START.date(),
        planning_time=time(9, 0),
        actual_start_at=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
        actual_end_at=datetime(2026, 6, 15, 10, 30, tzinfo=UTC),
    )
    exclude = uuid.uuid4()

    result, query = await _check(
        target_slot=target,
        target_instance=_instance(target, _START, _START + timedelta(hours=2)),
        schedule=[existing],
        leader=Leader.create(name="Leader", district_id=target.district_id),
        exclude_assignment_id=exclude,
    )

    assert result[0].rule_id == "no_double_booking"
    assert result[0].severity is Severity.BLOCK
    query.assert_awaited_once()
    kwargs = query.await_args.kwargs
    assert kwargs["exclude_assignment_id"] == exclude
    assert kwargs["window_start"] < _START
    assert kwargs["window_end"] > _START + timedelta(hours=2)


@pytest.mark.asyncio
async def test_conflict_check_fails_closed_when_target_has_no_instance() -> None:
    """A slot without EventInstance is checked against its own planning time."""
    target = _slot()
    existing = ScheduledService(
        congregation_id=uuid.uuid4(), planning_date=_START.date(), planning_time=time(10, 30)
    )

    result, _ = await _check(
        target_slot=target, target_instance=None, schedule=[existing], leader=None
    )

    assert [c.rule_id for c in result] == ["no_double_booking"]


@pytest.mark.asyncio
async def test_conflict_check_passes_for_distant_services_without_instances() -> None:
    target = _slot()
    existing = ScheduledService(
        congregation_id=target.congregation_id, planning_date=_START.date(), planning_time=time(16)
    )

    result, _ = await _check(
        target_slot=target, target_instance=None, schedule=[existing], leader=None
    )

    assert result == []


def test_scheduled_service_window_prefers_actual_times() -> None:
    service = ScheduledService(
        congregation_id=None,
        planning_date=_START.date(),
        planning_time=time(10),
        actual_start_at=datetime(2026, 6, 15, 11, tzinfo=UTC),
        actual_end_at=datetime(2026, 6, 15, 12, tzinfo=UTC),
    )

    assert service.window(timedelta(minutes=90)) == (
        datetime(2026, 6, 15, 11, tzinfo=UTC),
        datetime(2026, 6, 15, 12, tzinfo=UTC),
    )


def test_scheduled_service_window_falls_back_to_planning_time_in_utc() -> None:
    service = ScheduledService(congregation_id=None, planning_date=_START.date(), planning_time=time(10))

    assert service.window(timedelta(minutes=90)) == (
        datetime(2026, 6, 15, 10, tzinfo=UTC),
        datetime(2026, 6, 15, 11, 30, tzinfo=UTC),
    )
