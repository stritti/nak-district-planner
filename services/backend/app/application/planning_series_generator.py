"""Planning series generator service.

Generates PlanningSlot + EventInstance pairs from active PlanningSeries
for a rolling window (default 6-12 months ahead).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_series import PlanningSeries
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.repositories import (
    CongregationRepository,
    DistrictRepository,
    EventInstanceRepository,
    PlanningSeriesRepository,
    PlanningSlotRepository,
)


@dataclass(frozen=True)
class GeneratedSlot:
    """A single generated slot from a series recurrence expansion."""

    planning_date: date
    planning_time: timedelta  # minutes from midnight
    category: str | None
    title: str | None


def _expand_recurrence(
    series: PlanningSeries,
    *,
    from_date: date,
    to_date_exclusive: date,
    timezone_name: str = "Europe/Berlin",
) -> list[GeneratedSlot]:
    """Expand a PlanningSeries recurrence pattern into concrete slot dates.

    Supports simple weekly recurrence:
      {"type": "weekly", "days": [0, 1, 2, 3, 4, 5, 6]}
    where day numbers match Python's weekday (0=Monday, 6=Sunday).

    Falls back to weekly on the series' default_planning_time day of week
    if no pattern is specified.
    """
    pattern = series.recurrence_pattern or {}
    pattern_type = pattern.get("type", "weekly")
    slots: list[GeneratedSlot] = []
    _tz = ZoneInfo(timezone_name)

    if pattern_type == "weekly":
        days: list[int] = pattern.get("days", [series.created_at.weekday()])
        current = from_date
        while current < to_date_exclusive:
            if current.weekday() in days:
                planning_time = (
                    timedelta(
                        hours=series.default_planning_time.hour,
                        minutes=series.default_planning_time.minute,
                    )
                    if series.default_planning_time
                    else timedelta(hours=10)
                )
                slots.append(
                    GeneratedSlot(
                        planning_date=current,
                        planning_time=planning_time,
                        category=series.category,
                        title=None,
                    )
                )
            current += timedelta(days=1)
    # Future: add monthly, biweekly patterns here

    return slots


class PlanningSeriesGenerator:
    """Generate PlanningSlot + EventInstance from active PlanningSeries."""

    def __init__(
        self,
        *,
        series_repo: PlanningSeriesRepository,
        slot_repo: PlanningSlotRepository,
        instance_repo: EventInstanceRepository,
        district_repo: DistrictRepository,
        congregation_repo: CongregationRepository,
        timezone_name: str = "Europe/Berlin",
        horizon_months: int = 12,
    ) -> None:
        self._series_repo = series_repo
        self._slot_repo = slot_repo
        self._instance_repo = instance_repo
        self._district_repo = district_repo
        self._congregation_repo = congregation_repo
        self._timezone_name = timezone_name
        self._horizon_months = horizon_months

    async def run(self, now: datetime | None = None) -> dict[str, int]:
        """Generate slots for all active series.

        Returns summary dict with created / skipped counts.
        """
        now = now or datetime.now(UTC)
        from_date = now.date()
        to_date = self._add_months(from_date, self._horizon_months)

        return await self.run_for_window(from_date=from_date, to_date_exclusive=to_date)

    async def run_for_window(
        self,
        *,
        from_date: date,
        to_date_exclusive: date,
        district_ids: set[uuid.UUID] | None = None,
    ) -> dict[str, int]:
        """Generate slots for a specific window, optionally filtered by district."""
        if to_date_exclusive <= from_date:
            return {"series_processed": 0, "slots_created": 0, "slots_skipped": 0}

        series_list = await self._series_repo.list_active()
        created = 0
        skipped = 0
        processed_series = 0

        for series in series_list:
            if district_ids is not None and series.district_id not in district_ids:
                continue

            processed_series += 1
            effective_from = max(from_date, series.active_from or from_date)
            effective_to = min(to_date_exclusive, series.active_until or to_date_exclusive)
            if effective_to <= effective_from:
                skipped += 1
                continue

            generated = _expand_recurrence(
                series,
                from_date=effective_from,
                to_date_exclusive=effective_to,
                timezone_name=self._timezone_name,
            )

            for gslot in generated:
                # Check if slot already exists for this date/series/congregation
                existing_slot = await self._slot_repo.get_by_series_date(
                    series_id=series.id,
                    planning_date=gslot.planning_date,
                    congregation_id=series.congregation_id,
                )
                if existing_slot is not None:
                    skipped += 1
                    continue

                # Create PlanningSlot
                planning_time = (
                    datetime.combine(gslot.planning_date, datetime.min.time()) + gslot.planning_time
                ).time()

                slot = PlanningSlot.create(
                    series_id=series.id,
                    district_id=series.district_id,
                    congregation_id=series.congregation_id,
                    category=gslot.category or series.category,
                    title=gslot.title,
                    planning_date=gslot.planning_date,
                    planning_time=planning_time,
                    status=PlanningSlotStatus.ACTIVE,
                )
                await self._slot_repo.save(slot)

                # Create EventInstance
                instance = EventInstance.create(
                    planning_slot_id=slot.id,
                    title=gslot.title or "Gottesdienst",
                    actual_start_at=datetime.combine(
                        gslot.planning_date, planning_time, tzinfo=UTC
                    ),
                    actual_end_at=datetime.combine(gslot.planning_date, planning_time, tzinfo=UTC)
                    + timedelta(hours=1, minutes=30),
                    source=EventSource.INTERNAL,
                    visibility=EventVisibility.INTERNAL,
                    deviation_flag=False,
                )
                await self._instance_repo.save(instance)
                created += 1

        return {
            "series_processed": processed_series,
            "slots_created": created,
            "slots_skipped": skipped,
        }

    @staticmethod
    def _add_months(source: date, months: int) -> date:
        """Add months to a date, clamping to end-of-month if needed."""
        month = source.month - 1 + months
        year = source.year + month // 12
        month = month % 12 + 1
        import calendar

        day = min(source.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
