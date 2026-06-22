"""app/application/planning_series_service.py: PlanningSeries slot generation service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.models.planning_series import PlanningSeries
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.planning_series_service import PlanningSeriesSlotGenerator
from app.domain.ports.repositories import (
    PlanningSeriesRepository,
    PlanningSlotRepository,
)


@dataclass(frozen=True)
class RecurrenceRule:
    """Parsed recurrence rule for PlanningSeries."""

    frequency: str  # "weekly", "monthly", "yearly"
    interval: int = 1
    by_weekday: list[int] | None = None  # 0=Monday, 6=Sunday
    by_month_day: int | None = None
    by_month: int | None = None
    count: int | None = None  # Number of occurrences
    until: date | None = None


class PlanningSeriesSlotGenerationService(PlanningSeriesSlotGenerator):
    """Service for generating PlanningSlots from PlanningSeries templates.

    This service implements the Soll/Ist separation by:
    - Creating PlanningSlots from PlanningSeries (Soll)
    - Never allowing external changes to mutate PlanningSeries
    - Supporting rolling generation 6-12 months ahead
    """

    def __init__(
        self,
        series_repo: PlanningSeriesRepository,
        slot_repo: PlanningSlotRepository,
        timezone_name: str = "Europe/Berlin",
        default_horizon_months: int = 6,
    ) -> None:
        self._series_repo = series_repo
        self._slot_repo = slot_repo
        self._timezone_name = timezone_name
        self._default_horizon_months = default_horizon_months

    def _parse_recurrence_pattern(self, pattern: dict[str, any]) -> RecurrenceRule:
        """Parse recurrence pattern dict into structured rule."""
        return RecurrenceRule(
            frequency=pattern.get("frequency", "weekly"),
            interval=pattern.get("interval", 1),
            by_weekday=pattern.get("by_weekday"),
            by_month_day=pattern.get("by_month_day"),
            by_month=pattern.get("by_month"),
            count=pattern.get("count"),
            until=pattern.get("until"),
        )

    def _get_weekday_from_date(self, date_obj: date) -> int:
        """Get weekday as int (0=Monday, 6=Sunday)."""
        return date_obj.weekday()

    def _expand_weekly_series(
        self,
        series: PlanningSeries,
        from_date: date,
        to_date: date,
    ) -> list[date]:
        """Expand weekly recurrence pattern to list of dates."""
        rule = self._parse_recurrence_pattern(series.recurrence_pattern)

        # Default to series default_planning_time's weekday if not specified
        if rule.by_weekday is None:
            # Use the weekday from the default time (assuming it's a typical service day)
            # For weekly series without explicit weekday, use the day of the week
            # when the series was created or activated
            default_weekday = self._get_weekday_from_date(
                series.active_from or from_date
            )
            rule = RecurrenceRule(
                frequency=rule.frequency,
                interval=rule.interval,
                by_weekday=[default_weekday],
                until=rule.until,
            )

        # Find the first date >= from_date that matches one of the weekdays
        current = from_date
        while current.weekday() not in (rule.by_weekday or []):
            current += timedelta(days=1)
            if current > to_date:
                return []

        dates: list[date] = []

        while current <= to_date:
            dates.append(current)
            current += timedelta(days=rule.interval * 7)

        return dates

    def _expand_monthly_series(
        self,
        series: PlanningSeries,
        from_date: date,
        to_date: date,
    ) -> list[date]:
        """Expand monthly recurrence pattern to list of dates."""
        rule = self._parse_recurrence_pattern(series.recurrence_pattern)

        dates: list[date] = []
        current_year = from_date.year
        current_month = from_date.month

        while True:
            # Calculate target day in month
            if rule.by_month_day:
                target_day = rule.by_month_day
            else:
                # Default to the day of the month from active_from or 1st
                target_day = (series.active_from or from_date).day

            # Try to create date for current month
            try:
                candidate = date(current_year, current_month, target_day)
            except ValueError:
                # Invalid date (e.g., Feb 30), skip to next month
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
                continue

            if from_date <= candidate <= to_date:
                dates.append(candidate)

            # Move to next month
            current_month += rule.interval
            if current_month > 12:
                current_month = current_month % 12
                current_year += current_month // 12

            if date(current_year, current_month, 1) > to_date:
                break

        return dates

    def _expand_series_dates(
        self,
        series: PlanningSeries,
        from_date: date,
        to_date: date,
    ) -> list[date]:
        """Expand PlanningSeries to list of dates based on recurrence pattern."""
        rule = self._parse_recurrence_pattern(series.recurrence_pattern)

        if rule.frequency == "weekly":
            return self._expand_weekly_series(series, from_date, to_date)
        elif rule.frequency == "monthly":
            return self._expand_monthly_series(series, from_date, to_date)
        else:
            # Default: weekly on the same weekday as active_from or from_date
            return self._expand_weekly_series(series, from_date, to_date)

    def _create_slot_from_series(
        self,
        series: PlanningSeries,
        date_obj: date,
    ) -> PlanningSlot:
        """Create a PlanningSlot from a PlanningSeries for a specific date."""
        return PlanningSlot.create(
            district_id=series.district_id,
            planning_date=date_obj,
            planning_time=series.default_planning_time,
            series_id=series.id,
            congregation_id=series.congregation_id,
            category=series.category or "Gottesdienst",
            title=None,  # Will be set from EventInstance or default
            status=PlanningSlotStatus.ACTIVE,
        )

    async def generate_slots_for_series(
        self,
        series_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        """Generate PlanningSlots for a specific PlanningSeries."""
        series = await self._series_repo.get(series_id)
        if not series:
            return {"generated": 0, "skipped": 0, "updated": 0, "error": "Series not found"}

        if not series.is_active:
            return {"generated": 0, "skipped": 0, "updated": 0, "error": "Series inactive"}

        # Calculate date range
        today = date.today()
        effective_from = from_date or today
        effective_to = to_date or (effective_from + timedelta(days=30 * horizon_months))

        # Apply series date constraints
        if series.active_from:
            effective_from = max(effective_from, series.active_from)
        if series.active_until:
            effective_to = min(effective_to, series.active_until)

        if effective_from > effective_to:
            return {"generated": 0, "skipped": 0, "updated": 0}

        # Expand series to dates
        dates = self._expand_series_dates(series, effective_from, effective_to)

        generated = 0
        skipped = 0

        for date_obj in dates:
            # Check if slot already exists for this series and date
            existing = await self._slot_repo.get_by_series_and_date(
                series.id, date_obj
            )

            if existing:
                skipped += 1
                continue

            # Create new slot
            slot = self._create_slot_from_series(series, date_obj)
            await self._slot_repo.save(slot)
            generated += 1

        return {"generated": generated, "skipped": skipped, "updated": 0}

    async def generate_slots_for_district(
        self,
        district_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        """Generate PlanningSlots for all active series in a district."""
        # Get all active series for this district
        all_series = await self._series_repo.list_by_district(district_id)
        active_series = [s for s in all_series if s.is_active]

        total_generated = 0
        total_skipped = 0
        series_processed = 0

        for series in active_series:
            result = await self.generate_slots_for_series(
                series.id,
                from_date=from_date,
                to_date=to_date,
                horizon_months=horizon_months,
            )
            total_generated += result.get("generated", 0)
            total_skipped += result.get("skipped", 0)
            series_processed += 1

        return {
            "generated": total_generated,
            "skipped": total_skipped,
            "updated": 0,
            "series_processed": series_processed,
        }

    async def generate_all_slots(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        """Generate PlanningSlots for all active series across all districts."""
        # Get all active series
        all_series = await self._series_repo.list_all_active()

        total_generated = 0
        total_skipped = 0
        series_processed = 0
        districts_processed = set()

        for series in all_series:
            if not series.is_active:
                continue

            result = await self.generate_slots_for_series(
                series.id,
                from_date=from_date,
                to_date=to_date,
                horizon_months=horizon_months,
            )
            total_generated += result.get("generated", 0)
            total_skipped += result.get("skipped", 0)
            series_processed += 1
            districts_processed.add(series.district_id)

        return {
            "generated": total_generated,
            "skipped": total_skipped,
            "updated": 0,
            "series_processed": series_processed,
            "districts_processed": len(districts_processed),
        }
