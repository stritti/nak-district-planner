"""app/application/draft_service_generation.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.repositories import (
    CongregationRepository,
    DistrictRepository,
    EventInstanceRepository,
    PlanningSlotRepository,
)

DEFAULT_SERVICE_DURATION_MINUTES = 90


@dataclass(frozen=True)
class PlannedServiceSlot:
    slot_key: str
    start_at_utc: datetime
    end_at_utc: datetime


def expand_service_slots(
    *,
    service_times: list[dict],
    from_date: date,
    to_date_exclusive: date,
    timezone_name: str,
    duration_minutes: int = DEFAULT_SERVICE_DURATION_MINUTES,
) -> list[PlannedServiceSlot]:
    tz = ZoneInfo(timezone_name)
    slots: list[PlannedServiceSlot] = []

    current = from_date
    while current < to_date_exclusive:
        for service_time in service_times:
            weekday = service_time.get("weekday")
            if weekday != current.weekday():
                continue

            raw_time = service_time.get("time")
            if not isinstance(raw_time, str) or ":" not in raw_time:
                continue
            hour_text, minute_text = raw_time.split(":", 1)
            try:
                local_clock = time(hour=int(hour_text), minute=int(minute_text))
            except ValueError:
                continue

            local_start = datetime.combine(current, local_clock, tzinfo=tz)
            local_end = local_start + timedelta(minutes=duration_minutes)
            slot_key = f"{current.isoformat()}|{weekday}|{raw_time}"
            slots.append(
                PlannedServiceSlot(
                    slot_key=slot_key,
                    start_at_utc=local_start.astimezone(UTC),
                    end_at_utc=local_end.astimezone(UTC),
                )
            )
            break
        current += timedelta(days=1)

    return slots


def _planning_time_from_utc(dt: datetime, tz_name: str) -> time:
    """Extract local planning time from a UTC datetime."""
    return dt.astimezone(ZoneInfo(tz_name)).time()


class GenerateDraftServicesUseCase:
    def __init__(
        self,
        *,
        district_repo: DistrictRepository,
        congregation_repo: CongregationRepository,
        slot_repo: PlanningSlotRepository,
        instance_repo: EventInstanceRepository,
        timezone_name: str = "Europe/Berlin",
        horizon_weeks: int = 8,
    ) -> None:
        self._district_repo = district_repo
        self._congregation_repo = congregation_repo
        self._slot_repo = slot_repo
        self._instance_repo = instance_repo
        self._timezone_name = timezone_name
        self._horizon_weeks = horizon_weeks

    async def run(self, now: datetime | None = None) -> dict[str, int]:
        tz = ZoneInfo(self._timezone_name)
        now_local = (now or datetime.now(UTC)).astimezone(tz)
        from_date = now_local.date()
        to_date_exclusive = from_date + timedelta(weeks=self._horizon_weeks)
        return await self.run_for_window(from_date=from_date, to_date_exclusive=to_date_exclusive)

    async def run_for_window(
        self,
        *,
        from_date: date,
        to_date_exclusive: date,
        district_ids: set[uuid.UUID] | None = None,
    ) -> dict[str, int]:
        if to_date_exclusive <= from_date:
            return {
                "districts": 0,
                "congregations": 0,
                "created": 0,
                "skipped_existing": 0,
                "adopted_existing": 0,
                "invalid_configurations": 0,
            }

        districts = await self._district_repo.list_all()
        if district_ids is not None:
            districts = [district for district in districts if district.id in district_ids]
        created = 0
        skipped_existing = 0
        adopted_existing = 0
        invalid_configurations = 0
        congregations_seen = 0

        for district in districts:
            congregations = await self._congregation_repo.list_by_district(district.id)
            for congregation in congregations:
                congregations_seen += 1
                service_times = congregation.service_times or []
                if not service_times:
                    invalid_configurations += 1
                    continue

                slots = expand_service_slots(
                    service_times=service_times,
                    from_date=from_date,
                    to_date_exclusive=to_date_exclusive,
                    timezone_name=self._timezone_name,
                )

                if not slots:
                    invalid_configurations += 1
                    continue

                # Load existing gaps PlanningSlots for this congregation in the window
                existing_slots = await self._slot_repo.list_for_date_range(
                    district_id=district.id,
                    from_date=from_date,
                    to_date=(to_date_exclusive - timedelta(days=1)),
                )
                existing_for_congregation = {
                    (
                        slot.planning_date.isoformat(),
                        slot.planning_time.isoformat(),
                    )
                    for slot in existing_slots
                    if slot.congregation_id == congregation.id
                    and slot.category == "Gottesdienst"
                }

                for slot in slots:
                    planning_time = _planning_time_from_utc(
                        slot.start_at_utc, self._timezone_name
                    )
                    key = (slot.start_at_utc.date().isoformat(), planning_time.isoformat())

                    if key in existing_for_congregation:
                        skipped_existing += 1
                        continue

                    planning_slot = PlanningSlot.create(
                        district_id=district.id,
                        congregation_id=congregation.id,
                        category="Gottesdienst",
                        planning_date=slot.start_at_utc.date(),
                        planning_time=planning_time,
                        status=PlanningSlotStatus.ACTIVE,
                    )
                    await self._slot_repo.save(planning_slot)

                    instance = EventInstance.create(
                        planning_slot_id=planning_slot.id,
                        title=(
                            f"Gottesdienst {congregation.name}"
                            if congregation.name
                            else "Gottesdienst"
                        ),
                        actual_start_at=slot.start_at_utc,
                        actual_end_at=slot.end_at_utc,
                        source=EventSource.INTERNAL,
                        visibility=EventVisibility.PUBLIC,
                    )
                    await self._instance_repo.save(instance)
                    created += 1

        return {
            "districts": len(districts),
            "congregations": congregations_seen,
            "created": created,
            "skipped_existing": skipped_existing,
            "adopted_existing": adopted_existing,
            "invalid_configurations": invalid_configurations,
        }
