from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers.service_assignments import _raise_blocking_conflicts
from app.application.service_assignment_conflict import check_service_assignment_conflicts
from app.config import Settings
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.leader import Leader
from app.domain.models.planning_slot import PlanningSlot
from app.domain.models.service_assignment import ServiceAssignment
from app.domain.planning.conflict_result import ConflictResult, Severity


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


@pytest.mark.asyncio
async def test_conflict_adapter_returns_no_conflicts_for_missing_event_data() -> None:
    session = AsyncMock()
    with (
        patch("app.application.service_assignment_conflict.SqlPlanningSlotRepository") as slot_cls,
        patch(
            "app.application.service_assignment_conflict.SqlEventInstanceRepository"
        ) as instance_cls,
        patch("app.application.service_assignment_conflict.SqlLeaderRepository") as leader_cls,
    ):
        slot_cls.return_value.get = AsyncMock(return_value=None)
        instance_cls.return_value.get_by_planning_slot = AsyncMock(return_value=None)
        leader_cls.return_value.get = AsyncMock(return_value=None)

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


@pytest.mark.asyncio
async def test_conflict_adapter_builds_context_from_planning_data() -> None:
    leader_id = uuid.uuid4()
    target_event_id = uuid.uuid4()
    existing_event_id = uuid.uuid4()
    target_start = datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
    target_slot = PlanningSlot.create(
        district_id=uuid.uuid4(),
        planning_date=target_start.date(),
        planning_time=target_start.time(),
        congregation_id=uuid.uuid4(),
        slot_id=target_event_id,
    )
    existing_slot = PlanningSlot.create(
        district_id=target_slot.district_id,
        planning_date=target_start.date(),
        planning_time=target_start.time(),
        congregation_id=uuid.uuid4(),
        slot_id=existing_event_id,
    )
    target_instance = EventInstance.create(
        planning_slot_id=target_event_id,
        title="Ziel",
        actual_start_at=target_start,
        actual_end_at=datetime(2026, 6, 15, 12, 0, tzinfo=UTC),
        source=EventSource.INTERNAL,
        visibility=EventVisibility.PUBLIC,
    )
    existing_instance = EventInstance.create(
        planning_slot_id=existing_event_id,
        title="Bestehend",
        actual_start_at=datetime(2026, 6, 15, 9, 0, tzinfo=UTC),
        actual_end_at=datetime(2026, 6, 15, 10, 30, tzinfo=UTC),
        source=EventSource.INTERNAL,
        visibility=EventVisibility.PUBLIC,
    )
    existing_assignment = ServiceAssignment.create(
        event_id=existing_event_id,
        planning_slot_id=existing_event_id,
        leader_id=leader_id,
    )
    leader = Leader.create(name="Leader", district_id=target_slot.district_id)
    leader.id = leader_id
    session = AsyncMock()

    with (
        patch("app.application.service_assignment_conflict.SqlPlanningSlotRepository") as slot_cls,
        patch(
            "app.application.service_assignment_conflict.SqlEventInstanceRepository"
        ) as instance_cls,
        patch(
            "app.application.service_assignment_conflict.SqlServiceAssignmentRepository"
        ) as assignment_cls,
        patch("app.application.service_assignment_conflict.SqlLeaderRepository") as leader_cls,
        patch(
            "app.application.service_assignment_conflict.SqlLeaderUnavailabilityRepository"
        ) as absence_cls,
    ):
        slot_cls.return_value.get = AsyncMock(side_effect=[target_slot, existing_slot])
        instance_cls.return_value.get_by_planning_slot = AsyncMock(
            side_effect=[target_instance, existing_instance]
        )
        assignment_cls.return_value.list_by_leader = AsyncMock(return_value=[existing_assignment])
        leader_cls.return_value.get = AsyncMock(return_value=leader)
        absence_cls.return_value.list_overlapping = AsyncMock(return_value=[])

        result = await check_service_assignment_conflicts(
            session,
            event_id=target_event_id,
            leader_id=leader_id,
        )

    assert result[0].rule_id == "no_double_booking"
    assert result[0].severity is Severity.BLOCK
