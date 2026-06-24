"""app/domain/ports/planning_series_service.py: Ports for PlanningSeries slot generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
import uuid


class PlanningSeriesSlotGenerator(ABC):
    """Port for generating PlanningSlots from PlanningSeries."""

    @abstractmethod
    async def generate_slots_for_series(
        self,
        series_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        """Generate PlanningSlots for a specific series.
        
        Args:
            series_id: The PlanningSeries ID
            from_date: Optional start date (defaults to today)
            to_date: Optional end date (defaults to from_date + horizon_months)
            horizon_months: Number of months to generate ahead
            
        Returns:
            dict with keys: generated, skipped, updated
        """
        pass

    @abstractmethod
    async def generate_slots_for_district(
        self,
        district_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        """Generate PlanningSlots for all active series in a district.
        
        Args:
            district_id: The district ID
            from_date: Optional start date (defaults to today)
            to_date: Optional end date (defaults to from_date + horizon_months)
            horizon_months: Number of months to generate ahead
            
        Returns:
            dict with keys: generated, skipped, updated, series_processed
        """
        pass

    @abstractmethod
    async def generate_all_slots(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        """Generate PlanningSlots for all active series across all districts.
        
        Args:
            from_date: Optional start date (defaults to today)
            to_date: Optional end date (defaults to from_date + horizon_months)
            horizon_months: Number of months to generate ahead
            
        Returns:
            dict with keys: generated, skipped, updated, series_processed, districts_processed
        """
        pass
