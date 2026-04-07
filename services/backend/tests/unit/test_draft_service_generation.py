from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from app.application.draft_service_generation import (
    GenerateDraftServicesUseCase,
    expand_service_slots,
)
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.event import Event, EventStatus


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


class InMemoryEventRepo:
    def __init__(self) -> None:
        self.saved: list[Event] = []
        self.by_slot_key: dict[tuple[uuid.UUID, uuid.UUID, str], Event] = {}
        self.by_datetime: dict[tuple[uuid.UUID, uuid.UUID, datetime, datetime], Event] = {}

    async def get_by_generation_slot_key(
        self,
        *,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID,
        generation_slot_key: str,
    ) -> Event | None:
        return self.by_slot_key.get((district_id, congregation_id, generation_slot_key))

    async def get_matching_draft_service_slot(
        self,
        *,
        district_id: uuid.UUID,
        congregation_id: uuid.UUID,
        start_at: datetime,
        end_at: datetime,
    ) -> Event | None:
        event = self.by_datetime.get((district_id, congregation_id, start_at, end_at))
        if event is None:
            return None
        if event.category != "Gottesdienst" or event.status != EventStatus.DRAFT:
            return None
        return event

    async def save(self, event: Event) -> None:
        self.saved.append(event)
        if event.generation_slot_key is not None:
            self.by_slot_key[
                (event.district_id, event.congregation_id, event.generation_slot_key)
            ] = event
        self.by_datetime[
            (event.district_id, event.congregation_id, event.start_at, event.end_at)
        ] = event


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


async def test_use_case_creates_draft_without_assignment() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    event_repo = InMemoryEventRepo()

    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        event_repo=event_repo,
    )

    result = await use_case.run(now=datetime(2026, 4, 1, 8, 0, tzinfo=UTC))

    assert result["created"] > 0
    created = [event for event in event_repo.saved if event.generation_slot_key is not None]
    assert created
    assert all(event.status == EventStatus.DRAFT for event in created)
    assert all(event.category == "Gottesdienst" for event in created)


async def test_use_case_is_idempotent_on_second_run() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    event_repo = InMemoryEventRepo()

    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        event_repo=event_repo,
    )

    first = await use_case.run(now=datetime(2026, 4, 1, 8, 0, tzinfo=UTC))
    second = await use_case.run(now=datetime(2026, 4, 1, 8, 0, tzinfo=UTC))

    assert first["created"] > 0
    assert second["created"] == 0
    assert second["skipped_existing"] >= first["created"]


async def test_moved_event_blocks_regeneration_of_original_slot() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    event_repo = InMemoryEventRepo()

    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        event_repo=event_repo,
    )

    await use_case.run(now=datetime(2026, 5, 20, 8, 0, tzinfo=UTC))
    generated = next(iter(event_repo.by_slot_key.values()))
    original_slot_key = generated.generation_slot_key

    del event_repo.by_datetime[
        (generated.district_id, generated.congregation_id, generated.start_at, generated.end_at)
    ]
    generated.start_at = generated.start_at + timedelta(days=1)
    generated.end_at = generated.end_at + timedelta(days=1)
    await event_repo.save(generated)

    rerun = await use_case.run(now=datetime(2026, 5, 20, 8, 0, tzinfo=UTC))
    assert rerun["created"] == 0
    assert (district.id, congregation.id, original_slot_key) in event_repo.by_slot_key


async def test_existing_matching_slot_adopts_generation_key() -> None:
    district = _make_district()
    congregation = _make_congregation(district.id)
    event_repo = InMemoryEventRepo()

    slots = expand_service_slots(
        service_times=congregation.service_times,
        from_date=date(2026, 4, 1),
        to_date_exclusive=date(2026, 4, 30),
        timezone_name="Europe/Berlin",
    )
    first_slot = slots[0]

    existing = Event.create(
        title="Gottesdienst",
        start_at=first_slot.start_at_utc,
        end_at=first_slot.end_at_utc,
        district_id=district.id,
        congregation_id=congregation.id,
        category="Gottesdienst",
        status=EventStatus.DRAFT,
    )
    await event_repo.save(existing)

    use_case = GenerateDraftServicesUseCase(
        district_repo=InMemoryDistrictRepo([district]),
        congregation_repo=InMemoryCongregationRepo({district.id: [congregation]}),
        event_repo=event_repo,
    )

    result = await use_case.run(now=datetime(2026, 4, 1, 8, 0, tzinfo=UTC))
    assert result["adopted_existing"] >= 1
    assert existing.generation_slot_key is not None
