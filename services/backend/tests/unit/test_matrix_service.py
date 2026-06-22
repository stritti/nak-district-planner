"""tests/unit/test_matrix_service.py: Unit tests for MatrixService."""

from __future__ import annotations

import pytest
from datetime import date, datetime, time, timedelta
import uuid

from app.application.matrix_service import MatrixService
from app.domain.models.event_instance import EventInstance
from app.domain.models.event import EventSource, EventVisibility
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus


@pytest.fixture
def matrix_service():
    return MatrixService()


class TestMatrixService:
    """Tests for MatrixService."""
    
    def test_calculate_deviation_minutes_no_deviation(self, matrix_service):
        """Test deviation calculation when there's no deviation."""
        slot = PlanningSlot.create(
            district_id=uuid.uuid4(),
            planning_date=date(2026, 6, 22),
            planning_time=time(9, 30),
        )
        
        # Create instance with same times
        instance = EventInstance.create(
            planning_slot_id=slot.id,
            title="Gottesdienst",
            actual_start_at=datetime(2026, 6, 22, 9, 30),
            actual_end_at=datetime(2026, 6, 22, 11, 0),
            source=EventSource.INTERNAL,
            visibility=EventVisibility.INTERNAL,
        )
        
        start_diff, end_diff = matrix_service.calculate_deviation_minutes(
            slot, instance
        )
        
        assert start_diff is None
        assert end_diff is None
    
    def test_calculate_deviation_minutes_with_deviation(self, matrix_service):
        """Test deviation calculation when there's a deviation."""
        slot = PlanningSlot.create(
            district_id=uuid.uuid4(),
            planning_date=date(2026, 6, 22),
            planning_time=time(9, 30),
        )
        
        # Create instance with different times (+30 minutes)
        instance = EventInstance.create(
            planning_slot_id=slot.id,
            title="Gottesdienst",
            actual_start_at=datetime(2026, 6, 22, 10, 0),
            actual_end_at=datetime(2026, 6, 22, 11, 30),
            source=EventSource.INTERNAL,
            visibility=EventVisibility.INTERNAL,
        )
        
        start_diff, end_diff = matrix_service.calculate_deviation_minutes(
            slot, instance
        )
        
        assert start_diff == 30  # +30 minutes
        assert end_diff == 30   # +30 minutes
    
    def test_calculate_deviation_minutes_negative_deviation(self, matrix_service):
        """Test deviation calculation with negative difference."""
        slot = PlanningSlot.create(
            district_id=uuid.uuid4(),
            planning_date=date(2026, 6, 22),
            planning_time=time(10, 0),
        )
        
        # Create instance that starts earlier
        instance = EventInstance.create(
            planning_slot_id=slot.id,
            title="Gottesdienst",
            actual_start_at=datetime(2026, 6, 22, 9, 30),
            actual_end_at=datetime(2026, 6, 22, 11, 0),
            source=EventSource.INTERNAL,
            visibility=EventVisibility.INTERNAL,
        )
        
        start_diff, end_diff = matrix_service.calculate_deviation_minutes(
            slot, instance
        )
        
        assert start_diff == -30  # -30 minutes
        assert end_diff == -30   # -30 minutes
    
    def test_has_deviation_true(self, matrix_service):
        """Test has_deviation returns True when there's a deviation."""
        slot = PlanningSlot.create(
            district_id=uuid.uuid4(),
            planning_date=date(2026, 6, 22),
            planning_time=time(9, 30),
        )
        
        instance = EventInstance.create(
            planning_slot_id=slot.id,
            title="Gottesdienst",
            actual_start_at=datetime(2026, 6, 22, 10, 0),
            actual_end_at=datetime(2026, 6, 22, 11, 30),
            source=EventSource.INTERNAL,
            visibility=EventVisibility.INTERNAL,
        )
        
        assert matrix_service.has_deviation(slot, instance) is True
    
    def test_has_deviation_false(self, matrix_service):
        """Test has_deviation returns False when there's no deviation."""
        slot = PlanningSlot.create(
            district_id=uuid.uuid4(),
            planning_date=date(2026, 6, 22),
            planning_time=time(9, 30),
        )
        
        instance = EventInstance.create(
            planning_slot_id=slot.id,
            title="Gottesdienst",
            actual_start_at=datetime(2026, 6, 22, 9, 30),
            actual_end_at=datetime(2026, 6, 22, 11, 0),
            source=EventSource.INTERNAL,
            visibility=EventVisibility.INTERNAL,
        )
        
        assert matrix_service.has_deviation(slot, instance) is False
    
    def test_has_deviation_no_instance(self, matrix_service):
        """Test has_deviation returns False when there's no instance."""
        slot = PlanningSlot.create(
            district_id=uuid.uuid4(),
            planning_date=date(2026, 6, 22),
            planning_time=time(9, 30),
        )
        
        assert matrix_service.has_deviation(slot, None) is False
    
    def test_format_time(self, matrix_service):
        """Test time formatting."""
        assert matrix_service.format_time(time(9, 30)) == "09:30"
        assert matrix_service.format_time(time(14, 5)) == "14:05"
        assert matrix_service.format_time(None) == ""
    
    def test_format_datetime(self, matrix_service):
        """Test datetime formatting."""
        dt = datetime(2026, 6, 22, 9, 30, 0)
        assert matrix_service.format_datetime(dt) == "09:30"
        assert matrix_service.format_datetime(None) == ""
