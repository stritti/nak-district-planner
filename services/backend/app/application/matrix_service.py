"""app/application/matrix_service.py: Service for building matrix data with deviation detection."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta

from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import PlanningSlot


class MatrixService:
    """Service for building matrix view data with deviation detection and display logic.

    This service provides utilities for:
    - Calculating deviation details between PlanningSlots and EventInstances
    - Formatting time differences for display
    - Building matrix cell data with deviation information
    """

    @staticmethod
    def calculate_deviation_minutes(
        slot: PlanningSlot,
        instance: EventInstance,
        default_duration_minutes: int = 90,
    ) -> tuple[int | None, int | None]:
        """Calculate deviation in minutes between PlanningSlot and EventInstance.

        Args:
            slot: The PlanningSlot (Soll)
            instance: The EventInstance (Ist)
            default_duration_minutes: Default duration for events (default: 90)

        Returns:
            Tuple of (start_difference_minutes, end_difference_minutes)
            Returns (None, None) if no deviation
        """
        # Calculate expected times from slot
        expected_start = datetime.combine(slot.planning_date, slot.planning_time)
        expected_end = expected_start + timedelta(minutes=default_duration_minutes)

        # Get actual times (remove timezone for comparison)
        actual_start = instance.actual_start_at.replace(tzinfo=None)
        actual_end = instance.actual_end_at.replace(tzinfo=None)

        # Calculate differences
        start_diff = actual_start - expected_start
        end_diff = actual_end - expected_end

        start_diff_minutes = int(start_diff.total_seconds() / 60)
        end_diff_minutes = int(end_diff.total_seconds() / 60)

        # Only return if there's an actual deviation
        if start_diff_minutes == 0 and end_diff_minutes == 0:
            return (None, None)

        return (start_diff_minutes, end_diff_minutes)

    @staticmethod
    def format_time(time_obj: time | None) -> str:
        """Format time object for display (HH:MM)."""
        if not time_obj:
            return ""
        return time_obj.strftime("%H:%M")

    @staticmethod
    def format_datetime(dt: datetime | None) -> str:
        """Format datetime for display (HH:MM)."""
        if not dt:
            return ""
        return dt.strftime("%H:%M")

    @staticmethod
    def has_deviation(
        slot: PlanningSlot,
        instance: EventInstance | None,
        default_duration_minutes: int = 90,
    ) -> bool:
        """Check if there's a deviation between slot and instance."""
        if not instance:
            return False

        expected_start = datetime.combine(slot.planning_date, slot.planning_time)
        expected_end = expected_start + timedelta(minutes=default_duration_minutes)

        actual_start = instance.actual_start_at.replace(tzinfo=None)
        actual_end = instance.actual_end_at.replace(tzinfo=None)

        return actual_start != expected_start or actual_end != expected_end
