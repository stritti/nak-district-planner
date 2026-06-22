"""app/application/deviation_service.py: Service for detecting and managing deviations."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from app.domain.models.event_instance import EventInstance
from app.domain.models.planning_slot import PlanningSlot
from app.domain.ports.repositories import (
    EventInstanceRepository,
    PlanningSlotRepository,
)


class DeviationService:
    """Service for detecting and managing deviations between PlanningSlots and EventInstances.

    A deviation occurs when the actual_start_at/actual_end_at of an EventInstance
    differs from the planned planning_date/planning_time of its PlanningSlot.

    This service:
    - Automatically detects deviations when EventInstances are created/updated
    - Sets the deviation_flag on EventInstances
    - Provides utilities for checking and resolving deviations
    """

    def __init__(
        self,
        slot_repo: PlanningSlotRepository,
        instance_repo: EventInstanceRepository,
    ) -> None:
        self._slot_repo = slot_repo
        self._instance_repo = instance_repo

    def _calculate_expected_start(
        self,
        slot: PlanningSlot,
    ) -> datetime:
        """Calculate the expected start datetime from a PlanningSlot."""
        return datetime.combine(
            slot.planning_date,
            slot.planning_time,
        )

    def _calculate_expected_end(
        self,
        slot: PlanningSlot,
        duration_minutes: int = 90,
    ) -> datetime:
        """Calculate the expected end datetime from a PlanningSlot.

        Uses a default duration of 90 minutes if not specified otherwise.
        """
        from datetime import timedelta
        expected_start = self._calculate_expected_start(slot)
        return expected_start + timedelta(minutes=duration_minutes)

    def _has_deviation(
        self,
        slot: PlanningSlot,
        instance: EventInstance,
        duration_minutes: int = 90,
    ) -> bool:
        """Check if an EventInstance deviates from its PlanningSlot."""
        expected_start = self._calculate_expected_start(slot)
        expected_end = self._calculate_expected_end(slot, duration_minutes)

        # Compare with actual times (ignoring timezone for comparison)
        actual_start = instance.actual_start_at.replace(tzinfo=None)
        actual_end = instance.actual_end_at.replace(tzinfo=None)

        return actual_start != expected_start or actual_end != expected_end

    async def detect_and_update_deviation(
        self,
        instance: EventInstance,
        duration_minutes: int = 90,
    ) -> bool:
        """Detect deviation for an EventInstance and update its deviation_flag.

        Args:
            instance: The EventInstance to check
            duration_minutes: Expected duration in minutes (default: 90)

        Returns:
            True if deviation was detected and flag was set, False otherwise
        """
        slot = await self._slot_repo.get(instance.planning_slot_id)
        if not slot:
            # Orphaned instance - cannot determine deviation
            return False

        has_deviation = self._has_deviation(slot, instance, duration_minutes)

        if instance.deviation_flag != has_deviation:
            instance.deviation_flag = has_deviation
            await self._instance_repo.save(instance)
            return True

        return False

    async def detect_deviation_for_slot(
        self,
        slot_id: uuid.UUID,
        duration_minutes: int = 90,
    ) -> bool:
        """Detect deviation for all EventInstances of a PlanningSlot.

        Args:
            slot_id: The PlanningSlot ID
            duration_minutes: Expected duration in minutes (default: 90)

        Returns:
            True if any deviation was detected and updated
        """
        slot = await self._slot_repo.get(slot_id)
        if not slot:
            return False

        # Get all instances for this slot (should be 0 or 1 normally)
        instances = await self._instance_repo.list_by_planning_slot(slot_id)

        any_updated = False
        for instance in instances:
            updated = await self.detect_and_update_deviation(instance, duration_minutes)
            any_updated = any_updated or updated

        return any_updated

    async def resolve_deviation(
        self,
        instance_id: uuid.UUID,
    ) -> bool:
        """Manually resolve a deviation by aligning EventInstance with PlanningSlot.

        This updates the EventInstance's actual_start_at and actual_end_at
        to match the PlanningSlot's planned times.

        Args:
            instance_id: The EventInstance ID to resolve

        Returns:
            True if deviation was resolved, False if no deviation existed
        """
        instance = await self._instance_repo.get(instance_id)
        if not instance:
            return False

        slot = await self._slot_repo.get(instance.planning_slot_id)
        if not slot:
            return False

        if not instance.deviation_flag:
            # No deviation to resolve
            return False

        # Update instance times to match slot
        expected_start = datetime.combine(slot.planning_date, slot.planning_time)
        # Use same duration as current instance
        duration = instance.actual_end_at - instance.actual_start_at
        expected_end = expected_start + duration

        instance.actual_start_at = expected_start
        instance.actual_end_at = expected_end
        instance.deviation_flag = False

        await self._instance_repo.save(instance)
        return True

    async def get_deviation_details(
        self,
        instance_id: uuid.UUID,
        duration_minutes: int = 90,
    ) -> dict[str, any] | None:
        """Get detailed deviation information for an EventInstance.

        Args:
            instance_id: The EventInstance ID
            duration_minutes: Expected duration in minutes (default: 90)

        Returns:
            dict with deviation details or None if no deviation
        """
        instance = await self._instance_repo.get(instance_id)
        if not instance:
            return None

        slot = await self._slot_repo.get(instance.planning_slot_id)
        if not slot:
            return None

        if not instance.deviation_flag:
            return {
                "has_deviation": False,
                "planned_start": self._calculate_expected_start(slot).isoformat(),
                "planned_end": self._calculate_expected_end(slot, duration_minutes).isoformat(),
                "actual_start": instance.actual_start_at.isoformat(),
                "actual_end": instance.actual_end_at.isoformat(),
            }

        expected_start = self._calculate_expected_start(slot)
        expected_end = self._calculate_expected_end(slot, duration_minutes)

        actual_start = instance.actual_start_at.replace(tzinfo=None)
        actual_end = instance.actual_end_at.replace(tzinfo=None)

        return {
            "has_deviation": True,
            "planned_start": expected_start.isoformat(),
            "planned_end": expected_end.isoformat(),
            "actual_start": actual_start.isoformat(),
            "actual_end": actual_end.isoformat(),
            "start_difference_seconds": (actual_start - expected_start).total_seconds(),
            "end_difference_seconds": (actual_end - expected_end).total_seconds(),
        }
