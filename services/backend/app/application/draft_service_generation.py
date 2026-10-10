"""app/application/draft_service_generation.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.models.congregation import Congregation
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.repositories import (
    CongregationRepository,
    DistrictRepository,
    EventInstanceRepository,
    PlanningSlotRepository,
)

DEFAULT_SERVICE_DURATION_MINUTES = 90


DRAFT_SERVICE_KEY_PREFIX = "draft-service"


@dataclass(frozen=True)
class PlannedServiceSlot:
    slot_key: str
    start_at_utc: datetime
    end_at_utc: datetime
    local_date: date


def draft_service_generation_key(congregation_id: uuid.UUID, local_date: date) -> str:
    """Stable identity of a generated worship service: congregation + local date.

    The time is deliberately not part of the key: ``expand_service_slots``
    yields at most one service per congregation and day, and the key must stay
    the same when a planner moves the service or the configured time changes.
    """
    return f"{DRAFT_SERVICE_KEY_PREFIX}:{congregation_id}:{local_date.isoformat()}"


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
                    local_date=current,
                )
            )
            break
        current += timedelta(days=1)

    return slots


def _planning_time_from_utc(dt: datetime) -> time:
    """Extract the UTC planning time from a UTC datetime.

    planning_time is stored as UTC (naive wall-clock UTC), matching all
    readers (matrix, sync, deviation, events API). Local display is the
    frontend's responsibility.
    """
    return dt.astimezone(UTC).time()


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
        # Fixed lock order: two runs over several districts cannot deadlock.
        districts.sort(key=lambda district: district.id)
        created = 0
        skipped_existing = 0
        adopted_existing = 0
        invalid_configurations = 0
        congregations_seen = 0

        for district in districts:
            # Serializes concurrent runs (nightly task, manual trigger) per district
            # until commit, so they never race on the unique indexes.
            await self._slot_repo.lock_district_for_generation(district.id)
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

                outcome = await self._generate_for_congregation(
                    district_id=district.id,
                    congregation=congregation,
                    slots=slots,
                    from_date=from_date,
                    to_date_exclusive=to_date_exclusive,
                )
                created += outcome["created"]
                skipped_existing += outcome["skipped_existing"]
                adopted_existing += outcome["adopted_existing"]

        return {
            "districts": len(districts),
            "congregations": congregations_seen,
            "created": created,
            "skipped_existing": skipped_existing,
            "adopted_existing": adopted_existing,
            "invalid_configurations": invalid_configurations,
        }

    async def _generate_for_congregation(
        self,
        *,
        district_id: uuid.UUID,
        congregation: Congregation,
        slots: list[PlannedServiceSlot],
        from_date: date,
        to_date_exclusive: date,
    ) -> dict[str, int]:
        """Create missing drafts; an occurrence counts as existing in any of these cases.

        1. A slot carries its generation key — whatever its date, time or status
           (moved or CANCELLED by a planner).
        2. Legacy slot without key at the generated date/time (data from before
           the key existed): adopted and backfilled with the key. Counted in
           ``adopted_existing`` and, as a sub-category, in ``skipped_existing``.
        3. The insert hits a unique index (concurrent run, or another ACTIVE
           slot already occupies that date/time).
        """
        counts = {"created": 0, "skipped_existing": 0, "adopted_existing": 0}
        keyed = {draft_service_generation_key(congregation.id, s.local_date): s for s in slots}
        existing_keys = {
            slot.generation_key
            for slot in await self._slot_repo.list_by_generation_keys(
                district_id=district_id, generation_keys=keyed.keys()
            )
        }
        existing_keys.update(await self._slot_repo.list_deleted_generation_keys(
            district_id=district_id, generation_keys=keyed.keys()
        ))
        legacy_by_date_time = {
            (slot.planning_date, slot.planning_time): slot
            for slot in await self._slot_repo.list_for_date_range(
                district_id=district_id,
                # planning_date is the UTC date, which may differ by one day from
                # the local window bounds.
                from_date=from_date - timedelta(days=1),
                to_date=to_date_exclusive,
            )
            if slot.generation_key is None
            and slot.congregation_id == congregation.id
            and slot.category == "Gottesdienst"
        }

        for key, planned in keyed.items():
            if key in existing_keys:
                counts["skipped_existing"] += 1
                continue

            planning_date = planned.start_at_utc.date()
            planning_time = _planning_time_from_utc(planned.start_at_utc)
            legacy = legacy_by_date_time.pop((planning_date, planning_time), None)
            if legacy is not None:
                legacy.generation_key = key
                await self._slot_repo.save(legacy)
                counts["adopted_existing"] += 1
                counts["skipped_existing"] += 1
                continue

            planning_slot = PlanningSlot.create(
                district_id=district_id,
                congregation_id=congregation.id,
                category="Gottesdienst",
                planning_date=planning_date,
                planning_time=planning_time,
                status=PlanningSlotStatus.ACTIVE,
                generation_key=key,
            )
            if not await self._slot_repo.add_if_absent(planning_slot):
                counts["skipped_existing"] += 1
                continue

            instance = EventInstance.create(
                planning_slot_id=planning_slot.id,
                title=(
                    f"Gottesdienst {congregation.name}" if congregation.name else "Gottesdienst"
                ),
                actual_start_at=planned.start_at_utc,
                actual_end_at=planned.end_at_utc,
                source=EventSource.INTERNAL,
                visibility=EventVisibility.PUBLIC,
            )
            await self._instance_repo.save(instance)
            counts["created"] += 1

        return counts
