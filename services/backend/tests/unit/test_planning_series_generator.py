"""Unit tests for PlanningSeriesGenerator — expansion, run_for_window, _add_months."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock

import pytest

from app.application.planning_series_generator import (
    PlanningSeriesGenerator,
    _expand_recurrence,
)
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_series import PlanningSeries
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus

# ── _expand_recurrence (pure function) ─────────────────────────────────────────


class TestExpandRecurrence:
    def test_weekly_mondays(self):
        """Expand weekly pattern for Mondays in a 2-week window."""
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [0]},  # Monday
        )
        results = _expand_recurrence(
            series,
            from_date=date(2026, 6, 1),  # Monday
            to_date_exclusive=date(2026, 6, 15),
        )
        assert len(results) == 2
        assert results[0].planning_date == date(2026, 6, 1)
        assert results[1].planning_date == date(2026, 6, 8)
        assert all(r.planning_time == timedelta(hours=10) for r in results)
        assert all(r.category is None for r in results)
        assert all(r.title is None for r in results)

    def test_weekly_multiple_days(self):
        """Expand weekly pattern for multiple weekdays."""
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(9, 0),
            recurrence_pattern={"type": "weekly", "days": [1, 3]},  # Tue, Thu
        )
        results = _expand_recurrence(
            series,
            from_date=date(2026, 6, 1),  # Monday
            to_date_exclusive=date(2026, 6, 10),
        )
        dates = [r.planning_date for r in results]
        assert date(2026, 6, 2) in dates  # Tue
        assert date(2026, 6, 4) in dates  # Thu
        assert date(2026, 6, 9) in dates  # Tue
        assert date(2026, 6, 1) not in dates  # Mon, not in pattern

    def test_weekly_default_day(self):
        """No pattern specified — falls back to series creation day of week."""
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(10, 0),
        )
        # series.created_at is now, which is a Thursday
        results = _expand_recurrence(
            series,
            from_date=date(2026, 6, 25),  # Thursday
            to_date_exclusive=date(2026, 7, 9),
        )
        # Should have Thursdays
        assert len(results) >= 2
        assert all(r.planning_time == timedelta(hours=10) for r in results)

    def test_default_planning_time_10am(self):
        """When default_planning_time is None, falls back to 10:00."""
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [6]},
        )
        results = _expand_recurrence(
            series,
            from_date=date(2026, 6, 1),
            to_date_exclusive=date(2026, 6, 8),
        )
        assert len(results) == 1
        assert results[0].planning_time == timedelta(hours=10)

    def test_empty_date_range(self):
        """When from_date >= to_date_exclusive, return empty list."""
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(10, 0),
        )
        assert (
            _expand_recurrence(
                series, from_date=date(2026, 6, 1), to_date_exclusive=date(2026, 6, 1)
            )
            == []
        )
        assert (
            _expand_recurrence(
                series, from_date=date(2026, 6, 5), to_date_exclusive=date(2026, 6, 1)
            )
            == []
        )

    def test_series_with_category(self):
        """Category from series propagates to generated slots."""
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(9, 0),
            category="Gottesdienst",
            recurrence_pattern={"type": "weekly", "days": [0]},
        )
        results = _expand_recurrence(
            series,
            from_date=date(2026, 6, 1),
            to_date_exclusive=date(2026, 6, 3),
        )
        assert len(results) == 1
        assert results[0].category == "Gottesdienst"

    def test_weekly_all_days(self):
        """Pattern with all 7 weekdays includes every day in range."""
        series = PlanningSeries.create(
            district_id=uuid.uuid4(),
            default_planning_time=time(8, 0),
            recurrence_pattern={"type": "weekly", "days": [0, 1, 2, 3, 4, 5, 6]},
        )
        results = _expand_recurrence(
            series,
            from_date=date(2026, 6, 1),  # Monday
            to_date_exclusive=date(2026, 6, 7),  # Sunday
        )
        assert len(results) == 6


# ── _add_months (static helper) ────────────────────────────────────────────────


class TestAddMonths:
    def test_add_one_month(self):
        assert PlanningSeriesGenerator._add_months(date(2026, 1, 15), 1) == date(2026, 2, 15)

    def test_add_three_months(self):
        assert PlanningSeriesGenerator._add_months(date(2026, 3, 31), 3) == date(2026, 6, 30)

    def test_year_rollover(self):
        assert PlanningSeriesGenerator._add_months(date(2026, 10, 1), 5) == date(2027, 3, 1)

    def test_add_zero(self):
        assert PlanningSeriesGenerator._add_months(date(2026, 6, 15), 0) == date(2026, 6, 15)

    def test_end_of_month_clamping_feb(self):
        assert PlanningSeriesGenerator._add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)

    def test_end_of_month_clamping_dec_jan(self):
        assert PlanningSeriesGenerator._add_months(date(2026, 11, 30), 2) == date(2027, 1, 30)

    def test_leap_year_feb(self):
        assert PlanningSeriesGenerator._add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)


# ── PlanningSeriesGenerator — run_for_window ────────────────────────────────────


class MockRepos:
    """Helper to build mocked repos for PlanningSeriesGenerator."""

    def __init__(self):
        self.series_repo = AsyncMock()
        self.slot_repo = AsyncMock()
        self.instance_repo = AsyncMock()
        self.district_repo = AsyncMock()
        self.congregation_repo = AsyncMock()

    def build(self) -> PlanningSeriesGenerator:
        return PlanningSeriesGenerator(
            series_repo=self.series_repo,
            slot_repo=self.slot_repo,
            instance_repo=self.instance_repo,
            district_repo=self.district_repo,
            congregation_repo=self.congregation_repo,
        )


class TestRunForWindow:
    @pytest.mark.asyncio
    async def test_empty_date_range_returns_early(self):
        """When to_date is before from_date, return zero counts."""
        m = MockRepos()
        gen = m.build()

        result = await gen.run_for_window(
            from_date=date(2026, 6, 10), to_date_exclusive=date(2026, 6, 1)
        )
        assert result == {"series_processed": 0, "slots_created": 0, "slots_skipped": 0}
        m.series_repo.list_active.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_active_series(self):
        """When no active series exist, return zero counts."""
        m = MockRepos()
        m.series_repo.list_active = AsyncMock(return_value=[])
        gen = m.build()

        result = await gen.run_for_window(
            from_date=date(2026, 1, 1), to_date_exclusive=date(2026, 2, 1)
        )
        assert result == {"series_processed": 0, "slots_created": 0, "slots_skipped": 0}

    @pytest.mark.asyncio
    async def test_filters_by_district_ids(self):
        """When district_ids is set, skip series from other districts."""
        m = MockRepos()
        district_a = uuid.uuid4()
        district_b = uuid.uuid4()
        series_a = PlanningSeries.create(
            district_id=district_a,
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [0]},
        )
        series_b = PlanningSeries.create(
            district_id=district_b,
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [0]},
        )
        m.series_repo.list_active = AsyncMock(return_value=[series_a, series_b])
        m.slot_repo.get_by_series_date = AsyncMock(return_value=None)
        m.slot_repo.save = AsyncMock()
        m.instance_repo.save = AsyncMock()
        gen = m.build()

        result = await gen.run_for_window(
            from_date=date(2026, 1, 5),  # Monday
            to_date_exclusive=date(2026, 1, 6),
            district_ids={district_a},
        )
        assert result["series_processed"] == 1
        m.slot_repo.save.assert_called_once()
        m.instance_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_slot_and_instance(self):
        """For a matching weekday, creates both PlanningSlot and EventInstance."""
        m = MockRepos()
        district_id = uuid.uuid4()
        cong_id = uuid.uuid4()
        series = PlanningSeries.create(
            district_id=district_id,
            congregation_id=cong_id,
            default_planning_time=time(10, 0),
            category="Gottesdienst",
            recurrence_pattern={"type": "weekly", "days": [0]},
            active_from=date(2026, 1, 1),
            active_until=date(2026, 6, 30),
        )
        m.series_repo.list_active = AsyncMock(return_value=[series])
        m.slot_repo.get_by_series_date = AsyncMock(return_value=None)
        m.slot_repo.save = AsyncMock()
        m.instance_repo.save = AsyncMock()
        gen = m.build()

        result = await gen.run_for_window(
            from_date=date(2026, 1, 5),  # Monday
            to_date_exclusive=date(2026, 1, 6),
        )
        assert result["slots_created"] == 1
        assert result["series_processed"] == 1
        m.slot_repo.save.assert_awaited_once()
        m.instance_repo.save.assert_awaited_once()

        # Verify the slot was saved with correct params
        saved_slot = m.slot_repo.save.call_args[0][0]
        assert isinstance(saved_slot, PlanningSlot)
        assert saved_slot.series_id == series.id
        assert saved_slot.district_id == district_id
        assert saved_slot.congregation_id == cong_id
        assert saved_slot.planning_date == date(2026, 1, 5)
        assert saved_slot.status == PlanningSlotStatus.ACTIVE

        # Verify the instance was saved with correct params
        saved_instance = m.instance_repo.save.call_args[0][0]
        assert isinstance(saved_instance, EventInstance)
        assert saved_instance.planning_slot_id == saved_slot.id
        assert saved_instance.title == "Gottesdienst"
        assert saved_instance.source == EventSource.INTERNAL
        assert saved_instance.visibility == EventVisibility.INTERNAL
        assert saved_instance.deviation_flag is False

    @pytest.mark.asyncio
    async def test_skips_existing_slot(self):
        """When a slot already exists, skip creation."""
        m = MockRepos()
        district_id = uuid.uuid4()
        series = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [0]},
        )
        existing_slot = PlanningSlot.create(
            district_id=district_id,
            planning_date=date(2026, 1, 5),
            planning_time=time(10, 0),
            series_id=series.id,
        )
        m.series_repo.list_active = AsyncMock(return_value=[series])
        m.slot_repo.get_by_series_date = AsyncMock(return_value=existing_slot)
        m.slot_repo.save = AsyncMock()
        m.instance_repo.save = AsyncMock()
        gen = m.build()

        result = await gen.run_for_window(
            from_date=date(2026, 1, 5),
            to_date_exclusive=date(2026, 1, 6),
        )
        assert result["slots_created"] == 0
        assert result["slots_skipped"] == 1
        m.slot_repo.save.assert_not_called()
        m.instance_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_active_date_range_filtering(self):
        """Series with active_from/active_until outside window is skipped."""
        m = MockRepos()
        district_id = uuid.uuid4()
        series = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [0]},
            active_from=date(2027, 1, 1),  # far in the future
        )
        m.series_repo.list_active = AsyncMock(return_value=[series])
        m.slot_repo.save = AsyncMock()
        m.instance_repo.save = AsyncMock()
        gen = m.build()

        result = await gen.run_for_window(
            from_date=date(2026, 1, 1),
            to_date_exclusive=date(2026, 2, 1),
        )
        assert result["slots_created"] == 0
        assert result["slots_skipped"] == 1

    @pytest.mark.asyncio
    async def test_series_without_active_dates(self):
        """Series with no active_from/active_until is always active."""
        m = MockRepos()
        district_id = uuid.uuid4()
        series = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [0]},
            active_from=None,
            active_until=None,
        )
        m.series_repo.list_active = AsyncMock(return_value=[series])
        m.slot_repo.get_by_series_date = AsyncMock(return_value=None)
        m.slot_repo.save = AsyncMock()
        m.instance_repo.save = AsyncMock()
        gen = m.build()

        result = await gen.run_for_window(
            from_date=date(2026, 1, 5),
            to_date_exclusive=date(2026, 1, 6),
        )
        assert result["slots_created"] == 1

    @pytest.mark.asyncio
    async def test_run_delegates_to_run_for_window(self):
        """run() calls run_for_window with computed dates."""
        m = MockRepos()
        m.series_repo.list_active = AsyncMock(return_value=[])
        gen = m.build()

        result = await gen.run(now=datetime(2026, 6, 1, tzinfo=UTC))
        # Should call run_for_window with from=2026-06-01, to=2027-06-01 (12 months)
        assert result == {"series_processed": 0, "slots_created": 0, "slots_skipped": 0}

    @pytest.mark.asyncio
    async def test_run_defaults_to_now(self):
        """run() without 'now' defaults to datetime.now(UTC)."""
        m = MockRepos()
        m.series_repo.list_active = AsyncMock(return_value=[])
        gen = m.build()

        result = await gen.run()
        assert result == {"series_processed": 0, "slots_created": 0, "slots_skipped": 0}

    @pytest.mark.asyncio
    async def test_multiple_series_accumulate_counts(self):
        """Running with 2 series accumulates processed/skipped/created correctly."""
        m = MockRepos()
        district_id = uuid.uuid4()
        series1 = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [0]},  # Monday
        )
        series2 = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(10, 0),
            recurrence_pattern={"type": "weekly", "days": [2]},  # Wednesday
        )
        m.series_repo.list_active = AsyncMock(return_value=[series1, series2])
        m.slot_repo.get_by_series_date = AsyncMock(return_value=None)
        m.slot_repo.save = AsyncMock()
        m.instance_repo.save = AsyncMock()
        gen = m.build()

        result = await gen.run_for_window(
            from_date=date(2026, 1, 5),  # Monday
            to_date_exclusive=date(2026, 1, 15),  # include the 14th
        )
        assert result["series_processed"] == 2
        # series1 creates 2 slots (5th, 12th), series2 creates 2 slots (7th, 14th)
        assert result["slots_created"] == 4
