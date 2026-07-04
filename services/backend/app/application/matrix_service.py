"""app/application/matrix_service.py: Service for building matrix data with deviation detection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import PlanningSlot


@dataclass(frozen=True)
class _ExpectedTimes:
    """Expected start and end datetimes derived from a PlanningSlot."""
    expected_start: datetime
    expected_end: datetime


class MatrixService:
    """Service for building matrix view data with deviation detection and display logic.

    This service provides utilities for:
    - Calculating deviation details between PlanningSlots and EventInstances
    - Formatting time differences for display
    - Building matrix cell data with deviation information
    """

    @staticmethod
    def _expected_times(
        slot: PlanningSlot,
        default_duration_minutes: int = 90,
    ) -> _ExpectedTimes:
        """Compute expected start/end from a PlanningSlot (Soll-Zeiten)."""
        expected_start = datetime.combine(slot.planning_date, slot.planning_time)
        expected_end = expected_start + timedelta(minutes=default_duration_minutes)
        return _ExpectedTimes(expected_start=expected_start, expected_end=expected_end)

    @staticmethod
    def _actual_times(instance: EventInstance) -> tuple[datetime, datetime]:
        """Return actual start/end with tzinfo stripped for comparison."""
        return (
            instance.actual_start_at.replace(tzinfo=None),
            instance.actual_end_at.replace(tzinfo=None),
        )

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
        exp = MatrixService._expected_times(slot, default_duration_minutes)
        actual_start, actual_end = MatrixService._actual_times(instance)

        start_diff_minutes = int((actual_start - exp.expected_start).total_seconds() / 60)
        end_diff_minutes = int((actual_end - exp.expected_end).total_seconds() / 60)

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

        exp = MatrixService._expected_times(slot, default_duration_minutes)
        actual_start, actual_end = MatrixService._actual_times(instance)

        return actual_start != exp.expected_start or actual_end != exp.expected_end
