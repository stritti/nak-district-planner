from __future__ import annotations

import uuid
from collections.abc import Collection
from datetime import UTC, date, datetime, time, timedelta, timezone

from app.application.draft_service_generation import (
    GenerateDraftServicesUseCase,
    draft_service_generation_key,
    expand_service_slots,
)
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.repositories import EventInstanceRepository, PlanningSlotRepository

# ── In-memory fakes ──────────────────────────────────────────────────────


class InMemoryDistrictRepo:
    def __init__(self, districts: list[District]) -> None:
        self._districts = districts

    async def list_all(self) -> list[District]:
        return list(self._districts)


class InMemoryCongregationRepo:
    def __init__(self, congregation_by_district: dict[uuid.UUID, list[Congregation]]) -> None:
        self._congregation_by_district = congregation_by_district

    async def list_by_district(
        self, district_id: uuid.UUID, group_id: uuid.UUID | None = None
    ) -> list[Congregation]:
        return list(self._congregation_by_district.get(district_id, []))


class InMemoryPlanningSlotRepo(PlanningSlotRepository):
    def __init__(self) -> None:
        self._slots: dict[uuid.UUID, PlanningSlot] = {}

    async def get(self, slot_id: uuid.UUID) -> PlanningSlot | None:
        return self._slots.get(slot_id)

    async def get_by_series_and_date(
        self, series_id: uuid.UUID, planning_date: date
    ) -> PlanningSlot | None:
        for slot in self._slots.values():
            if slot.series_id == series_id and slot.planning_date == planning_date:
                return slot
        return None

    async def get_by_series_date(
        self,
        *,
        series_id: uuid.UUID,
        planning_date: date,
        congregation_id: uuid.UUID | None,
    ) -> PlanningSlot | None:
        for slot in self._slots.values():
            if (
                slot.series_id == series_id
                and slot.planning_date == planning_date
                and slot.congregation_id == congregation_id
            ):
                return slot
        return None

    async def list_for_date_range(
        self,
        *,
        district_id: uuid.UUID,
        from_date: date,
        to_date: date,
    ) -> list[PlanningSlot]:
        return [
            slot
            for slot in self._slots.values()
            if slot.district_id == district_id and from_date <= slot.planning_date <= to_date
        ]

    async def list_by_generation_keys(
        self, *, district_id: uuid.UUID, generation_keys: Collection[str]
    ) -> list[PlanningSlot]:
        keys = set(generation_keys)
        return [
            slot
            for slot in self._slots.values()
            if slot.district_id == district_id and slot.generation_key in keys
        ]

    async def delete(self, slot_id: uuid.UUID) -> None:
        self._slots.pop(slot_id, None)

    async def save(self, slot: PlanningSlot) -> None:
        self._slots[slot.id] = slot

    async def add_if_absent(self, slot: PlanningSlot) -> bool:
        """Mirror the two partial unique indexes of planning_slots."""
        for other in self._slots.values():
            same_key = (
                slot.generation_key is not None
                and other.district_id == slot.district_id
                and other.generation_key == slot.generation_key
            )
            same_active_time = (
                slot.congregation_id is not None
                and slot.status == other.status == PlanningSlotStatus.ACTIVE
                and (other.congregation_id, other.planning_date, other.planning_time)
                == (slot.congregation_id, slot.planning_date, slot.planning_time)
            )
            if same_key or same_active_time:
                return False
        self._slots[slot.id] = slot
        return True


class InMemoryEventInstanceRepo(EventInstanceRepository):
    def __init__(self) -> None:
        self._instances: dict[uuid.UUID, EventInstance] = {}

    async def get(self, instance_id: uuid.UUID) -> EventInstance | None:
        return self._instances.get(instance_id)

    async def list_by_planning_slot(self, planning_slot_id: uuid.UUID) -> list[EventInstance]:
        return [
            inst for inst in self._instances.values() if inst.planning_slot_id == planning_slot_id
        ]

    async def get_by_planning_slot(self, planning_slot_id: uuid.UUID) -> EventInstance | None:
        for inst in self._instances.values():
            if inst.planning_slot_id == planning_slot_id:
                return inst
        return None

    async def list_by_planning_slots(
        self, planning_slot_ids: list[uuid.UUID]
    ) -> list[EventInstance]:
        ids_set = set(planning_slot_ids)
        return [inst for inst in self._instances.values() if inst.planning_slot_id in ids_set]

    async def delete(self, instance_id: uuid.UUID) -> None:
        self._instances.pop(instance_id, None)

    async def save(self, instance: EventInstance) -> None:
        self._instances[instance.id] = instance

    async def get_by_external_uid(
        self, external_uid: str, calendar_integration_id: uuid.UUID
    ) -> EventInstance | None:
        return None

    async def list_by_calendar_integration(
        self, calendar_integration_id: uuid.UUID
    ) -> list[EventInstance]:
        return []


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_district() -> District:
    now = datetime.now(UTC)
    return District(id=uuid.uuid4(), name="Test", created_at=now, updated_at=now)


def _make_congregation(
    district_id: uuid.UUID, service_times: list[dict] | None = None
) -> Congregation:
    now = datetime.now(UTC)
    return Congregation(
        id=uuid.uuid4(),
        name="Gemeinde",
        district_id=district_id,
        service_times=service_times
        if service_times is not None
        else [{"weekday": 2, "time": "20:00"}],
        created_at=now,
        updated_at=now,
    )


# ── expand_service_slots tests (unchanged — pure function) ────────────────


def test_expand_service_slots_honors_horizon_and_weekday() -> None:
    slots = expand_service_slots(
        service_times=[{"weekday": 2, "time": "20:00"}],
        from_date=date(2026, 4, 1),
        to_date_exclusive=date(2026, 4, 15),
        timezone_name="Europe/Berlin",
    )
    assert len(slots) == 2
    assert slots[0].slot_key.startswith("2026-04-01|2|20:00")
    assert slots[1].slot_key.startswith("2026-04-08|2|20:00")


def test_expand_service_slots_is_timezone_aware_and_handles_dst() -> None:
    slots = expand_service_slots(
        service_times=[{"weekday": 6, "time": "09:30"}],
        from_date=date(2026, 3, 22),
        to_date_exclusive=date(2026, 4, 6),
        timezone_name="Europe/Berlin",
    )
    assert len(slots) == 3
    assert slots[0].start_at_utc.hour == 8
    assert slots[1].start_at_utc.hour == 7
    assert slots[2].start_at_utc.hour == 7
    assert (slots[0].end_at_utc - slots[0].start_at_utc) == timedelta(minutes=90)
    assert (slots[2].end_at_utc - slots[2].start_at_utc) == timedelta(minutes=90)


def test_planning_time_is_utc_not_local() -> None:
    """_planning_time_from_utc returns UTC wall-clock, matching all readers."""
    from app.application.draft_service_generation import _planning_time_from_utc

    assert _planning_time_from_utc(datetime(2026, 4, 1, 18, 0, tzinfo=UTC)) == time(18, 0)
    assert _planning_time_from_utc(datetime(2026, 1, 4, 8, 30, tzinfo=UTC)) == time(8, 30)


# ── Use case tests ──────────────────────────────────────────────────────


async def test_use_case_creates_planning_slots_and_instances() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    instance_repo = InMemoryEventInstanceRepo()

    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        slot_repo=slot_repo,
        instance_repo=instance_repo,
    )

    result = await use_case.run(now=datetime(2026, 4, 1, 8, 0, tzinfo=UTC))

    assert result["created"] > 0
    assert result["invalid_configurations"] == 0
    # Verify that PlanningSlots and EventInstances were created
    assert len(slot_repo._slots) == result["created"]
    assert len(instance_repo._instances) == result["created"]
    # All created slots should be "Gottesdienst" category
    for slot in slot_repo._slots.values():
        assert slot.category == "Gottesdienst"
        assert slot.congregation_id == congregation.id
    # All created instances should have INTERNAL source
    for inst in instance_repo._instances.values():
        assert inst.source == EventSource.INTERNAL


async def test_use_case_is_idempotent_on_second_run() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    instance_repo = InMemoryEventInstanceRepo()

    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        slot_repo=slot_repo,
        instance_repo=instance_repo,
    )

    first = await use_case.run(now=datetime(2026, 4, 1, 8, 0, tzinfo=UTC))
    second = await use_case.run(now=datetime(2026, 4, 1, 8, 0, tzinfo=UTC))

    assert first["created"] > 0
    assert second["created"] == 0
    assert second["skipped_existing"] >= first["created"]
    # Total stored slots should stay the same (no duplicates)
    assert len(slot_repo._slots) == first["created"]


async def test_skips_congregations_without_service_times() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id, service_times=[])
    slot_repo = InMemoryPlanningSlotRepo()
    instance_repo = InMemoryEventInstanceRepo()

    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        slot_repo=slot_repo,
        instance_repo=instance_repo,
    )

    result = await use_case.run(now=datetime(2026, 4, 1, 8, 0, tzinfo=UTC))

    assert result["created"] == 0
    assert result["invalid_configurations"] >= 1


async def test_respects_district_ids_filter() -> None:
    district_a = _make_district()
    district_b = _make_district()
    cong_a = _make_congregation(district_a.id)
    cong_b = _make_congregation(district_b.id)
    slot_repo = InMemoryPlanningSlotRepo()
    instance_repo = InMemoryEventInstanceRepo()

    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district_a, district_b]),
        congregation_repo=InMemoryCongregationRepo(
            {
                district_a.id: [cong_a],
                district_b.id: [cong_b],
            }
        ),
        slot_repo=slot_repo,
        instance_repo=instance_repo,
    )

    result = await use_case.run_for_window(
        from_date=date(2026, 4, 1),
        to_date_exclusive=date(2026, 4, 15),
        district_ids={district_a.id},
    )

    assert result["created"] > 0
    # Only district_a should have been processed
    for slot_id in slot_repo._slots:
        assert slot_repo._slots[slot_id].district_id == district_a.id


# ── expand_service_slots edge cases ────────────────────────────────────


def test_expand_service_slots_skips_invalid_time_value() -> None:
    """When service_time has no valid 'time' field, it should be skipped."""
    slots = expand_service_slots(
        service_times=[{"weekday": 2}, {"weekday": 2, "time": "20:00"}],
        from_date=date(2026, 4, 1),
        to_date_exclusive=date(2026, 4, 15),
        timezone_name="Europe/Berlin",
    )
    # Only the entry with a valid time should produce a slot
    assert len(slots) == 2
    assert all(s.slot_key.endswith("|20:00") for s in slots)


def test_expand_service_slots_skips_invalid_time_string() -> None:
    """When service_time has an unparseable time string, it should be skipped."""
    slots = expand_service_slots(
        service_times=[
            {"weekday": 2, "time": "abc"},
            {"weekday": 2, "time": "99:99"},
        ],
        from_date=date(2026, 4, 1),
        to_date_exclusive=date(2026, 4, 15),
        timezone_name="Europe/Berlin",
    )
    assert len(slots) == 0  # Both service times are invalid


# ── GenerateDraftServicesUseCase edge cases ─────────────────────────────


async def test_run_for_window_empty_range() -> None:
    """When to_date_exclusive <= from_date, result should be zero."""
    district = _make_district()
    congregation = _make_congregation(district.id)
    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        slot_repo=InMemoryPlanningSlotRepo(),
        instance_repo=InMemoryEventInstanceRepo(),
    )

    result = await use_case.run_for_window(
        from_date=date(2026, 4, 10),
        to_date_exclusive=date(2026, 4, 10),  # same as from_date
    )

    assert result["created"] == 0
    assert result["invalid_configurations"] == 0


async def test_run_for_window_all_slots_invalid() -> None:
    """When all service times produce no valid slots, count as invalid configs."""
    district = _make_district()
    # Service time with invalid time string
    congregation = _make_congregation(
        district.id,
        service_times=[{"weekday": 2, "time": "ungültig"}],
    )
    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        slot_repo=InMemoryPlanningSlotRepo(),
        instance_repo=InMemoryEventInstanceRepo(),
    )

    result = await use_case.run_for_window(
        from_date=date(2026, 4, 1),
        to_date_exclusive=date(2026, 4, 15),
    )

    assert result["created"] == 0
    assert result["invalid_configurations"] >= 1


# ── Generator key (issue #488) ───────────────────────────────────────────


async def test_generated_draft_moved_by_planner_is_not_regenerated() -> None:
    """A draft the planner moved to another time must not be re-created."""
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    instance_repo = InMemoryEventInstanceRepo()
    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        slot_repo=slot_repo,
        instance_repo=instance_repo,
    )
    window = {"from_date": date(2026, 4, 1), "to_date_exclusive": date(2026, 4, 8)}

    first = await use_case.run_for_window(**window)
    assert first["created"] == 1
    (slot,) = slot_repo._slots.values()
    slot.planning_time = time(17, 30)  # planner moves 20:00 local -> 19:30 local

    second = await use_case.run_for_window(**window)

    assert second["created"] == 0
    assert len(slot_repo._slots) == 1
    assert len(instance_repo._instances) == 1


def _use_case(district, congregation, slot_repo, instance_repo) -> GenerateDraftServicesUseCase:
    return GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        slot_repo=slot_repo,
        instance_repo=instance_repo,
    )


ONE_WEEK = {"from_date": date(2026, 4, 1), "to_date_exclusive": date(2026, 4, 8)}


async def test_generated_slot_carries_stable_generation_key() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    await _use_case(district, congregation, slot_repo, InMemoryEventInstanceRepo()).run_for_window(
        **ONE_WEEK
    )

    (slot,) = slot_repo._slots.values()
    assert slot.generation_key == draft_service_generation_key(congregation.id, date(2026, 4, 1))
    assert slot.generation_key == f"draft-service:{congregation.id}:2026-04-01"


async def test_generated_draft_moved_to_other_day_is_not_regenerated() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    use_case = _use_case(district, congregation, slot_repo, InMemoryEventInstanceRepo())
    await use_case.run_for_window(**ONE_WEEK)
    (slot,) = slot_repo._slots.values()
    slot.planning_date = date(2026, 4, 20)  # moved outside the generation window

    second = await use_case.run_for_window(**ONE_WEEK)

    assert second["created"] == 0
    assert second["skipped_existing"] == 1
    assert len(slot_repo._slots) == 1


async def test_cancelled_generated_slot_is_not_recreated() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    use_case = _use_case(district, congregation, slot_repo, InMemoryEventInstanceRepo())
    await use_case.run_for_window(**ONE_WEEK)
    (slot,) = slot_repo._slots.values()
    slot.status = PlanningSlotStatus.CANCELLED

    second = await use_case.run_for_window(**ONE_WEEK)

    assert second["created"] == 0
    assert [s.status for s in slot_repo._slots.values()] == [PlanningSlotStatus.CANCELLED]


async def test_legacy_slot_without_key_is_adopted_and_backfilled() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    legacy = PlanningSlot.create(
        district_id=district.id,
        congregation_id=congregation.id,
        category="Gottesdienst",
        planning_date=date(2026, 4, 1),
        planning_time=time(18, 0),  # 20:00 Europe/Berlin (CEST) in UTC
    )
    await slot_repo.save(legacy)
    use_case = _use_case(district, congregation, slot_repo, InMemoryEventInstanceRepo())

    first = await use_case.run_for_window(**ONE_WEEK)

    assert (first["created"], first["adopted_existing"]) == (0, 1)
    assert legacy.generation_key == draft_service_generation_key(congregation.id, date(2026, 4, 1))
    # Converged: once moved, the backfilled legacy slot is still recognised.
    legacy.planning_time = time(17, 30)
    second = await use_case.run_for_window(**ONE_WEEK)
    assert second["created"] == 0
    assert second["skipped_existing"] == 1
    assert len(slot_repo._slots) == 1


async def test_cancelled_legacy_slot_is_adopted_not_resurrected() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    legacy = PlanningSlot.create(
        district_id=district.id,
        congregation_id=congregation.id,
        category="Gottesdienst",
        planning_date=date(2026, 4, 1),
        planning_time=time(18, 0),
        status=PlanningSlotStatus.CANCELLED,
    )
    await slot_repo.save(legacy)

    result = await _use_case(
        district, congregation, slot_repo, InMemoryEventInstanceRepo()
    ).run_for_window(**ONE_WEEK)

    assert result["created"] == 0
    assert result["adopted_existing"] == 1
    assert len(slot_repo._slots) == 1


async def test_insert_rejected_by_unique_rule_is_skipped_without_instance() -> None:
    """A concurrent run that inserted the same key first makes this insert a no-op."""
    district = _make_district()
    congregation = _make_congregation(district.id)
    slot_repo = InMemoryPlanningSlotRepo()
    instance_repo = InMemoryEventInstanceRepo()
    use_case = _use_case(district, congregation, slot_repo, instance_repo)
    key = draft_service_generation_key(congregation.id, date(2026, 4, 1))
    concurrent = PlanningSlot.create(
        district_id=district.id,
        congregation_id=congregation.id,
        category="Gottesdienst",
        planning_date=date(2026, 4, 1),
        planning_time=time(18, 0),
        generation_key=key,
    )

    async def no_keys(**_: object) -> list[PlanningSlot]:
        # Simulate the race: the concurrent row is not visible to the lookup.
        return []

    slot_repo.list_by_generation_keys = no_keys  # type: ignore[method-assign]
    slot_repo._slots[concurrent.id] = concurrent

    result = await use_case.run_for_window(**ONE_WEEK)

    assert result["created"] == 0
    assert result["skipped_existing"] == 1
    assert len(slot_repo._slots) == 1
    assert instance_repo._instances == {}
