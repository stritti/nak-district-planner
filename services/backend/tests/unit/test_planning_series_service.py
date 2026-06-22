"""tests/unit/test_planning_series_service.py: Unit tests for PlanningSeriesSlotGenerationService."""

from __future__ import annotations

import pytest
from datetime import date, time
import uuid

from app.application.planning_series_service import PlanningSeriesSlotGenerationService
from app.domain.models.planning_series import PlanningSeries
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus


class MockPlanningSeriesRepository:
    """Mock repository for PlanningSeries."""
    
    def __init__(self):
        self.series_list: list[PlanningSeries] = []
        self.series_by_id: dict[uuid.UUID, PlanningSeries] = {}
    
    async def get(self, series_id: uuid.UUID) -> PlanningSeries | None:
        return self.series_by_id.get(series_id)
    
    async def list_by_district(self, district_id: uuid.UUID) -> list[PlanningSeries]:
        return [s for s in self.series_list if s.district_id == district_id]
    
    async def list_all_active(self) -> list[PlanningSeries]:
        return [s for s in self.series_list if s.is_active]
    
    async def save(self, series: PlanningSeries) -> None:
        self.series_list.append(series)
        self.series_by_id[series.id] = series


class MockPlanningSlotRepository:
    """Mock repository for PlanningSlot."""
    
    def __init__(self):
        self.slots: list[PlanningSlot] = []
        self.slots_by_id: dict[uuid.UUID, PlanningSlot] = {}
    
    async def get(self, slot_id: uuid.UUID) -> PlanningSlot | None:
        return self.slots_by_id.get(slot_id)
    
    async def get_by_series_and_date(
        self, series_id: uuid.UUID, planning_date: date
    ) -> PlanningSlot | None:
        # Check if any slot exists for this series and date
        for slot in self.slots:
            if slot.series_id == series_id and slot.planning_date == planning_date:
                return slot
        return None
    
    async def list_for_date_range(
        self,
        *,
        district_id: uuid.UUID,
        from_date: date,
        to_date: date,
    ) -> list[PlanningSlot]:
        return [
            s for s in self.slots
            if s.district_id == district_id
            and from_date <= s.planning_date <= to_date
        ]
    
    async def save(self, slot: PlanningSlot) -> None:
        self.slots.append(slot)
        self.slots_by_id[slot.id] = slot


class TestPlanningSeriesSlotGenerationService:
    """Tests for PlanningSeriesSlotGenerationService."""
    
    @pytest.mark.asyncio
    async def test_generate_slots_for_series_weekly(self):
        """Test generating weekly slots from a series."""
        series_repo = MockPlanningSeriesRepository()
        slot_repo = MockPlanningSlotRepository()
        service = PlanningSeriesSlotGenerationService(
            series_repo=series_repo,
            slot_repo=slot_repo,
        )
        
        district_id = uuid.uuid4()
        series = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(9, 30),
            recurrence_pattern={"frequency": "weekly", "interval": 1, "by_weekday": [6]},  # Sunday
            active_from=date(2026, 1, 1),
            active_until=date(2026, 12, 31),
        )
        await series_repo.save(series)
        
        result = await service.generate_slots_for_series(
            series_id=series.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
            horizon_months=1,
        )
        
        assert result["generated"] == 4  # 4 Sundays in January 2026
        assert result["skipped"] == 0
        assert len(slot_repo.slots) == 4
        
        # Check that all slots have correct time
        for slot in slot_repo.slots:
            assert slot.planning_time == time(9, 30)
            assert slot.series_id == series.id
    
    @pytest.mark.asyncio
    async def test_generate_slots_for_series_monthly(self):
        """Test generating monthly slots from a series."""
        series_repo = MockPlanningSeriesRepository()
        slot_repo = MockPlanningSlotRepository()
        service = PlanningSeriesSlotGenerationService(
            series_repo=series_repo,
            slot_repo=slot_repo,
        )
        
        district_id = uuid.uuid4()
        series = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(10, 0),
            recurrence_pattern={"frequency": "monthly", "interval": 1, "by_month_day": 1},
            active_from=date(2026, 1, 1),
            active_until=date(2026, 6, 30),
        )
        await series_repo.save(series)
        
        result = await service.generate_slots_for_series(
            series_id=series.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 6, 30),
            horizon_months=6,
        )
        
        assert result["generated"] == 6  # 6 months
        assert result["skipped"] == 0
        
        # Check that all slots are on the 1st of the month
        for slot in slot_repo.slots:
            assert slot.planning_date.day == 1
            assert slot.planning_time == time(10, 0)
    
    @pytest.mark.asyncio
    async def test_generate_slots_skips_existing(self):
        """Test that existing slots are skipped."""
        series_repo = MockPlanningSeriesRepository()
        slot_repo = MockPlanningSlotRepository()
        service = PlanningSeriesSlotGenerationService(
            series_repo=series_repo,
            slot_repo=slot_repo,
        )
        
        district_id = uuid.uuid4()
        series = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(9, 30),
            recurrence_pattern={"frequency": "weekly", "interval": 1, "by_weekday": [6]},
        )
        await series_repo.save(series)
        
        # Generate first time
        await service.generate_slots_for_series(
            series_id=series.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )
        
        first_count = len(slot_repo.slots)
        
        # Generate again - should skip existing
        result = await service.generate_slots_for_series(
            series_id=series.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )
        
        assert result["generated"] == 0
        assert result["skipped"] == first_count
        assert len(slot_repo.slots) == first_count
    
    @pytest.mark.asyncio
    async def test_generate_slots_for_district(self):
        """Test generating slots for all series in a district."""
        series_repo = MockPlanningSeriesRepository()
        slot_repo = MockPlanningSlotRepository()
        service = PlanningSeriesSlotGenerationService(
            series_repo=series_repo,
            slot_repo=slot_repo,
        )
        
        district_id = uuid.uuid4()
        
        # Create two series
        series1 = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(9, 0),
            recurrence_pattern={"frequency": "weekly", "interval": 1, "by_weekday": [6]},
        )
        series2 = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(10, 0),
            recurrence_pattern={"frequency": "weekly", "interval": 1, "by_weekday": [0]},  # Monday
        )
        
        await series_repo.save(series1)
        await series_repo.save(series2)
        
        result = await service.generate_slots_for_district(
            district_id=district_id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )
        
        # Should have slots from both series
        assert result["series_processed"] == 2
        assert result["generated"] > 0
    
    @pytest.mark.asyncio
    async def test_inactive_series_not_generated(self):
        """Test that inactive series are not generated."""
        series_repo = MockPlanningSeriesRepository()
        slot_repo = MockPlanningSlotRepository()
        service = PlanningSeriesSlotGenerationService(
            series_repo=series_repo,
            slot_repo=slot_repo,
        )
        
        district_id = uuid.uuid4()
        series = PlanningSeries.create(
            district_id=district_id,
            default_planning_time=time(9, 30),
            recurrence_pattern={"frequency": "weekly", "interval": 1, "by_weekday": [6]},
            is_active=False,
        )
        await series_repo.save(series)
        
        result = await service.generate_slots_for_series(
            series_id=series.id,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )
        
        assert result["generated"] == 0
        assert "error" in result
        assert "inactive" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_series_not_found(self):
        """Test handling of non-existent series."""
        series_repo = MockPlanningSeriesRepository()
        slot_repo = MockPlanningSlotRepository()
        service = PlanningSeriesSlotGenerationService(
            series_repo=series_repo,
            slot_repo=slot_repo,
        )
        
        result = await service.generate_slots_for_series(
            series_id=uuid.uuid4(),
            from_date=date(2026, 1, 1),
            to_date=date(2026, 1, 31),
        )
        
        assert result["generated"] == 0
        assert "error" in result
        assert "not found" in result["error"].lower()
