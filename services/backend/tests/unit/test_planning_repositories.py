"""Unit tests for PlanningSeries, PlanningSlot, and EventInstance SQL repos."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.models.event import EventSource, EventVisibility
from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_series import PlanningSeries
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.repositories import (
    EventInstanceRepository,
    PlanningSeriesRepository,
    PlanningSlotRepository,
)


def _make_execute_result(rows):
    """Build a mock execute result that returns rows via scalars().all()."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


# ── SqlPlanningSeriesRepository ───────────────────────────────────────────────


class TestSqlPlanningSeriesRepository:
    @pytest.fixture
    def session(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, session):
        from app.adapters.db.repositories.planning_series import SqlPlanningSeriesRepository

        return SqlPlanningSeriesRepository(session)

    async def test_get_found(self, repo: PlanningSeriesRepository, session):
        series_id = uuid.uuid4()
        session.get = AsyncMock(
            return_value=MagicMock(
                id=series_id,
                district_id=uuid.uuid4(),
                congregation_id=None,
                category="Gottesdienst",
                default_planning_time=time(10, 0),
                recurrence_pattern=None,
                active_from=None,
                active_until=None,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await repo.get(series_id)
        assert result is not None
        assert result.category == "Gottesdienst"

    async def test_get_not_found(self, repo: PlanningSeriesRepository, session):
        session.get = AsyncMock(return_value=None)
        assert await repo.get(uuid.uuid4()) is None

    async def test_list_all(self, repo: PlanningSeriesRepository, session):
        row = MagicMock(
            id=uuid.uuid4(),
            district_id=uuid.uuid4(),
            congregation_id=None,
            category="Gottesdienst",
            default_planning_time=time(10, 0),
            recurrence_pattern=None,
            active_from=None,
            active_until=None,
            is_active=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.execute = AsyncMock(return_value=_make_execute_result([row]))
        results = await repo.list_all()
        assert len(results) == 1
        assert results[0].category == "Gottesdienst"

    async def test_list_by_district(self, repo: PlanningSeriesRepository, session):
        session.execute = AsyncMock(return_value=_make_execute_result([]))
        results = await repo.list_by_district(uuid.uuid4())
        assert results == []

    async def test_list_all_active(self, repo: PlanningSeriesRepository, session):
        session.execute = AsyncMock(return_value=_make_execute_result([]))
        results = await repo.list_all_active()
        assert results == []

    async def test_save_new(self, repo: PlanningSeriesRepository, session):
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(10, 0),
        )
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        await repo.save(series)
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_save_existing(self, repo: PlanningSeriesRepository, session):
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(10, 0),
        )
        session.get = AsyncMock(return_value=MagicMock())  # already exists
        session.add = MagicMock()
        session.flush = AsyncMock()
        await repo.save(series)
        session.add.assert_not_called()
        session.flush.assert_awaited_once()


# ── SqlPlanningSlotRepository ─────────────────────────────────────────────────


class TestSqlPlanningSlotRepository:
    @pytest.fixture
    def session(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, session):
        from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository

        return SqlPlanningSlotRepository(session)

    async def test_get_found(self, repo: PlanningSlotRepository, session):
        slot_id = uuid.uuid4()
        session.get = AsyncMock(
            return_value=MagicMock(
                id=slot_id,
                series_id=uuid.uuid4(),
                district_id=uuid.uuid4(),
                congregation_id=None,
                category="Gottesdienst",
                title=None,
                approval_status=None,
                invitation_source_congregation_id=None,
                invitation_source_event_id=None,
                applicability=None,
                planning_date=date(2026, 6, 1),
                planning_time=time(10, 0),
                status="ACTIVE",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await repo.get(slot_id)
        assert result is not None
        assert result.category == "Gottesdienst"

    async def test_get_not_found(self, repo: PlanningSlotRepository, session):
        session.get = AsyncMock(return_value=None)
        assert await repo.get(uuid.uuid4()) is None

    async def test_get_by_series_date(self, repo: PlanningSlotRepository, session):
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = MagicMock(
            id=uuid.uuid4(),
            series_id=uuid.uuid4(),
            district_id=uuid.uuid4(),
            congregation_id=uuid.uuid4(),
            category="Gottesdienst",
            title=None,
            approval_status=None,
            invitation_source_congregation_id=None,
            invitation_source_event_id=None,
            applicability=[],
            planning_date=date(2026, 6, 1),
            planning_time=time(10, 0),
            status="ACTIVE",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.execute = AsyncMock(return_value=execute_result)
        slot = await repo.get_by_series_date(
            series_id=uuid.uuid4(), planning_date=date(2026, 6, 1), congregation_id=uuid.uuid4()
        )
        assert slot is not None
        assert slot.planning_date == date(2026, 6, 1)

    async def test_get_by_series_date_not_found(self, repo: PlanningSlotRepository, session):
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        slot = await repo.get_by_series_date(
            series_id=uuid.uuid4(), planning_date=date(2026, 6, 1), congregation_id=None
        )
        assert slot is None

    async def test_list_for_date_range(self, repo: PlanningSlotRepository, session):
        execute_result = _make_execute_result([])
        session.execute = AsyncMock(return_value=execute_result)
        result = await repo.list_for_date_range(
            district_id=uuid.uuid4(), from_date=date(2026, 1, 1), to_date=date(2026, 12, 31)
        )
        assert result == []

    async def test_save_new(self, repo: PlanningSlotRepository, session):
        slot = PlanningSlot.create(
            district_id=uuid.uuid4(),
            planning_date=date(2026, 6, 1),
            planning_time=time(10, 0),
        )
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        await repo.save(slot)
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_save_existing(self, repo: PlanningSlotRepository, session):
        slot = PlanningSlot.create(
            district_id=uuid.uuid4(),
            planning_date=date(2026, 6, 1),
            planning_time=time(10, 0),
        )
        session.get = AsyncMock(return_value=MagicMock())
        session.add = MagicMock()
        session.flush = AsyncMock()
        await repo.save(slot)
        session.add.assert_not_called()
        session.flush.assert_awaited_once()

    async def test_get_by_series_and_date(self, repo: PlanningSlotRepository, session):
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = MagicMock(
            id=uuid.uuid4(),
            series_id=uuid.uuid4(),
            district_id=uuid.uuid4(),
            congregation_id=None,
            category="Gottesdienst",
            title=None,
            approval_status=None,
            invitation_source_congregation_id=None,
            invitation_source_event_id=None,
            applicability=[],
            planning_date=date(2026, 6, 1),
            planning_time=time(10, 0),
            status="ACTIVE",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.execute = AsyncMock(return_value=execute_result)
        result = await repo.get_by_series_and_date(
            series_id=uuid.uuid4(), planning_date=date(2026, 6, 1)
        )
        assert result is not None
        assert result.planning_date == date(2026, 6, 1)


# ── SqlEventInstanceRepository ────────────────────────────────────────────────


class TestSqlEventInstanceRepository:
    @pytest.fixture
    def session(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, session):
        from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository

        return SqlEventInstanceRepository(session)

    async def test_get_found(self, repo: EventInstanceRepository, session):
        instance_id = uuid.uuid4()
        session.get = AsyncMock(
            return_value=MagicMock(
                id=instance_id,
                planning_slot_id=uuid.uuid4(),
                title="Gottesdienst",
                description=None,
                actual_start_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
                actual_end_at=datetime(2026, 6, 1, 11, 30, tzinfo=UTC),
                source="INTERNAL",
                visibility="INTERNAL",
                deviation_flag=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await repo.get(instance_id)
        assert result is not None
        assert result.title == "Gottesdienst"

    async def test_get_not_found(self, repo: EventInstanceRepository, session):
        session.get = AsyncMock(return_value=None)
        assert await repo.get(uuid.uuid4()) is None

    async def test_list_by_planning_slot(self, repo: EventInstanceRepository, session):
        row = MagicMock(
            id=uuid.uuid4(),
            planning_slot_id=uuid.uuid4(),
            title="Gottesdienst",
            description=None,
            actual_start_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            actual_end_at=datetime(2026, 6, 1, 11, 30, tzinfo=UTC),
            source="INTERNAL",
            visibility="INTERNAL",
            deviation_flag=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.execute = AsyncMock(return_value=_make_execute_result([row]))
        result = await repo.list_by_planning_slot(uuid.uuid4())
        assert len(result) == 1

    async def test_get_by_planning_slot(self, repo: EventInstanceRepository, session):
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = MagicMock(
            id=uuid.uuid4(),
            planning_slot_id=uuid.uuid4(),
            title="Gottesdienst",
            description=None,
            actual_start_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            actual_end_at=datetime(2026, 6, 1, 11, 30, tzinfo=UTC),
            source="INTERNAL",
            visibility="INTERNAL",
            deviation_flag=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.execute = AsyncMock(return_value=execute_result)
        result = await repo.get_by_planning_slot(uuid.uuid4())
        assert result is not None

    async def test_get_by_planning_slot_not_found(self, repo: EventInstanceRepository, session):
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=execute_result)
        result = await repo.get_by_planning_slot(uuid.uuid4())
        assert result is None

    async def test_list_by_planning_slots_empty(self, repo: EventInstanceRepository, session):
        result = await repo.list_by_planning_slots([])
        assert result == []

    async def test_list_by_planning_slots(self, repo: EventInstanceRepository, session):
        row = MagicMock(
            id=uuid.uuid4(),
            planning_slot_id=uuid.uuid4(),
            title="Gottesdienst",
            description=None,
            actual_start_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            actual_end_at=datetime(2026, 6, 1, 11, 30, tzinfo=UTC),
            source="INTERNAL",
            visibility="INTERNAL",
            deviation_flag=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.execute = AsyncMock(return_value=_make_execute_result([row]))
        result = await repo.list_by_planning_slots([uuid.uuid4()])
        assert len(result) == 1

    async def test_save_new(self, repo: EventInstanceRepository, session):
        instance = EventInstance.create(
            planning_slot_id=uuid.uuid4(),
            title="Gottesdienst",
            actual_start_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            actual_end_at=datetime(2026, 6, 1, 11, 30, tzinfo=UTC),
            source=EventSource.INTERNAL,
            visibility=EventVisibility.INTERNAL,
        )
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        await repo.save(instance)
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_save_existing(self, repo: EventInstanceRepository, session):
        instance = EventInstance.create(
            planning_slot_id=uuid.uuid4(),
            title="Gottesdienst",
            actual_start_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            actual_end_at=datetime(2026, 6, 1, 11, 30, tzinfo=UTC),
            source=EventSource.INTERNAL,
            visibility=EventVisibility.INTERNAL,
        )
        session.get = AsyncMock(return_value=MagicMock())
        session.add = MagicMock()
        session.flush = AsyncMock()
        await repo.save(instance)
        session.add.assert_not_called()
        session.flush.assert_awaited_once()
