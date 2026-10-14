# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Application-facing API facade for the one planning-series generator."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.application.planning_series_generator import PlanningSeriesGenerator
from app.domain.models.planning_series import PlanningSeries
from app.domain.ports.planning_series_service import PlanningSeriesSlotGenerator
from app.domain.ports.repositories import (
    EventInstanceRepository,
    PlanningSeriesRepository,
    PlanningSlotRepository,
)


class PlanningSeriesSlotGenerationService(PlanningSeriesSlotGenerator):
    """Expose the historical API response contract without duplicating generation."""

    def __init__(
        self,
        series_repo: PlanningSeriesRepository,
        slot_repo: PlanningSlotRepository,
        instance_repo: EventInstanceRepository,
        timezone_name: str = "Europe/Berlin",
    ) -> None:
        self._series_repo = series_repo
        self._generator = PlanningSeriesGenerator(
            series_repo=series_repo,
            slot_repo=slot_repo,
            instance_repo=instance_repo,
            timezone_name=timezone_name,
        )

    async def _generate(
        self,
        series: PlanningSeries,
        *,
        from_date: date | None,
        to_date: date | None,
        horizon_months: int,
    ) -> dict[str, int]:
        if not series.is_active:
            return {"generated": 0, "skipped": 0, "updated": 0, "error": "Series inactive"}

        start = from_date or date.today()
        end = to_date or start + timedelta(days=30 * horizon_months)
        start = max(start, series.active_from or start)
        end = min(end, series.active_until or end)
        if start > end:
            return {"generated": 0, "skipped": 0, "updated": 0}

        result = await self._generator.run_for_window(
            from_date=start,
            to_date_exclusive=end + timedelta(days=1),
            series_list=[series],
        )
        return {
            "generated": result["slots_created"],
            "skipped": result["slots_skipped"],
            "updated": 0,
        }

    async def generate_slots_for_series(
        self,
        series_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        series = await self._series_repo.get(series_id)
        if series is None:
            return {"generated": 0, "skipped": 0, "updated": 0, "error": "Series not found"}
        return await self._generate(
            series, from_date=from_date, to_date=to_date, horizon_months=horizon_months
        )

    async def generate_slots_for_district(
        self,
        district_id: uuid.UUID,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        series = sorted(
            (s for s in await self._series_repo.list_by_district(district_id) if s.is_active),
            key=lambda item: item.id,
        )
        generated = skipped = 0
        for item in series:
            result = await self._generate(
                item, from_date=from_date, to_date=to_date, horizon_months=horizon_months
            )
            generated += result["generated"]
            skipped += result["skipped"]
        return {
            "generated": generated,
            "skipped": skipped,
            "updated": 0,
            "series_processed": len(series),
        }

    async def generate_all_slots(
        self,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        horizon_months: int = 6,
    ) -> dict[str, int]:
        series = sorted(
            (s for s in await self._series_repo.list_all_active() if s.is_active),
            key=lambda item: (item.district_id, item.id),
        )
        generated = skipped = 0
        for item in series:
            result = await self._generate(
                item, from_date=from_date, to_date=to_date, horizon_months=horizon_months
            )
            generated += result["generated"]
            skipped += result["skipped"]
        return {
            "generated": generated,
            "skipped": skipped,
            "updated": 0,
            "series_processed": len(series),
            "districts_processed": len({item.district_id for item in series}),
        }
