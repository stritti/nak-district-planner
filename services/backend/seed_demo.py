# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Demo district for presentations: a filled matrix with the typical planning situations.

The scenario is relative to the run date: six weeks of services from the Monday of the
current week. It contains confirmed and planned services, a gap, a double booking, a
travel-time warning, an absence, an organist duty that collides with a service and the
church holidays. ``plan_demo`` is pure and decides who leads which service;
``seed_demo_district`` writes it with the application's repositories.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.district import SqlDistrictRepository
from app.adapters.db.repositories.event_duties import SqlEventDutiesRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.export_token import SqlExportTokenRepository
from app.adapters.db.repositories.leader import SqlLeaderRepository
from app.adapters.db.repositories.leader_unavailability import (
    SqlLeaderUnavailabilityRepository,
)
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.adapters.db.repositories.service_assignment import SqlServiceAssignmentRepository
from app.application.draft_service_generation import (
    DEFAULT_SERVICE_DURATION_MINUTES,
    GenerateDraftServicesUseCase,
)
from app.application.feiertage_service import import_kirchliche_festtage
from app.domain.models.congregation import Congregation
from app.domain.models.district import District
from app.domain.models.event_duty import EventDutyAssignment, EventDutyCategory
from app.domain.models.export_token import ExportToken, TokenType
from app.domain.models.leader import Leader, LeaderRank, SpecialRole
from app.domain.models.leader_unavailability import LeaderUnavailability, UnavailabilityReason
from app.domain.models.planning_slot import EventApprovalStatus
from app.domain.models.service_assignment import AssignmentStatus, ServiceAssignment

DEMO_DISTRICT_NAME = "Demo-Bezirk Aremorica"
DEMO_STATE_CODE = "BW"
DEMO_TIMEZONE = "Europe/Berlin"
DEMO_WEEKS = 6
DEMO_TOKEN_LABEL = "Demo: öffentliches Kalender-Abo"
ORGANIST_NAME = "Troubadix"

SUNDAY, WEDNESDAY, THURSDAY = 6, 2, 3

# Aquarium starts 15 minutes after Gallisches Dorf ends: leading both is a travel-time warning.
DEMO_CONGREGATIONS: dict[str, list[dict]] = {
    "Gallisches Dorf": [{"weekday": WEDNESDAY, "time": "20:00"}, {"weekday": SUNDAY, "time": "09:30"}],
    "Babaorum": [{"weekday": SUNDAY, "time": "09:30"}],
    "Aquarium": [{"weekday": SUNDAY, "time": "11:15"}],
    "Laudanum": [{"weekday": THURSDAY, "time": "20:00"}, {"weekday": SUNDAY, "time": "10:00"}],
}


@dataclass(frozen=True)
class DemoLeader:
    name: str
    rank: LeaderRank
    congregation: str | None = None
    role: SpecialRole | None = None


DISTRICT_ELDER = "Miraculix"
DEMO_LEADERS: tuple[DemoLeader, ...] = (
    DemoLeader(DISTRICT_ELDER, LeaderRank.BEZIRKSAELTESTER, role=SpecialRole.BEZIRKSVORSTEHER),
    DemoLeader("Majestix", LeaderRank.PRIESTER, "Gallisches Dorf", SpecialRole.GEMEINDEVORSTEHER),
    DemoLeader("Asterix", LeaderRank.EVANGELIST, "Gallisches Dorf"),
    DemoLeader("Obelix", LeaderRank.PRIESTER, "Babaorum", SpecialRole.GEMEINDEVORSTEHER),
    DemoLeader("Methusalix", LeaderRank.PRIESTER, "Aquarium", SpecialRole.GEMEINDEVORSTEHER),
    DemoLeader("Automatix", LeaderRank.PRIESTER, "Laudanum", SpecialRole.GEMEINDEVORSTEHER),
    DemoLeader("Verleihnix", LeaderRank.DIAKON, "Laudanum"),
)

# Who leads a service when nothing special happens that week.
SUNDAY_LEADER = {
    "Gallisches Dorf": "Majestix",
    "Babaorum": "Obelix",
    "Aquarium": "Methusalix",
    "Laudanum": "Automatix",
}
WEEKDAY_LEADER = {"Gallisches Dorf": "Asterix", "Laudanum": "Verleihnix"}


@dataclass(frozen=True)
class DemoService:
    """A generated worship service of the demo district."""

    slot_id: uuid.UUID
    congregation: str
    start_at: datetime  # UTC

    @property
    def end_at(self) -> datetime:
        return self.start_at + timedelta(minutes=DEFAULT_SERVICE_DURATION_MINUTES)


@dataclass(frozen=True)
class DemoPlan:
    """Who leads which service, what is released and which absences and duties exist."""

    leaders: dict[uuid.UUID, str]  # slot id -> leader name; slots without entry are gaps
    confirmed: frozenset[uuid.UUID]
    absences: tuple[tuple[str, datetime, datetime], ...]
    organist_duties: tuple[tuple[uuid.UUID, str], ...]  # (slot id, leader name or None=typed name)


def _week(service: DemoService, monday: date, tz: ZoneInfo) -> int:
    return (service.start_at.astimezone(tz).date() - monday).days // 7


def plan_demo(services: Iterable[DemoService], *, monday: date) -> DemoPlan:
    """Assign the demo leaders with one intentional example of each planning situation.

    Week 0-1 are released. Week 1: the district elder leads Gallisches Dorf and Babaorum at
    the same time (double booking). Week 2: he leads Gallisches Dorf and Aquarium 15 minutes
    apart (travel time). Week 3: Obelix is on vacation but still planned for
    Babaorum. Week 4: Automatix plays the organ in Babaorum while he leads
    Laudanum; Aquarium has no leader. Week 5: Laudanum and Gallisches Dorf's Wednesday
    service have no leader. Troubadix plays the organ in Gallisches Dorf every Sunday.
    """
    tz = ZoneInfo(DEMO_TIMEZONE)
    leaders: dict[uuid.UUID, str] = {}
    confirmed: set[uuid.UUID] = set()
    duties: list[tuple[uuid.UUID, str]] = []
    absences: list[tuple[str, datetime, datetime]] = []
    for service in sorted(services, key=lambda item: (item.start_at, item.congregation)):
        week = _week(service, monday, tz)
        is_sunday = service.start_at.astimezone(tz).weekday() == SUNDAY
        leader = (SUNDAY_LEADER if is_sunday else WEEKDAY_LEADER).get(service.congregation)
        if is_sunday and week == 1 and service.congregation in ("Gallisches Dorf", "Babaorum"):
            leader = DISTRICT_ELDER
        if is_sunday and week == 2 and service.congregation in ("Gallisches Dorf", "Aquarium"):
            leader = DISTRICT_ELDER
        if week == 4 and is_sunday and service.congregation == "Aquarium":
            leader = None
        if week == 5 and (
            (is_sunday and service.congregation == "Laudanum")
            or (not is_sunday and service.congregation == "Gallisches Dorf")
        ):
            leader = None
        if week == 3 and is_sunday and service.congregation == "Babaorum":
            local_day = service.start_at.astimezone(tz).date()
            start = datetime.combine(local_day - timedelta(days=2), time(0, 0), tzinfo=tz)
            absences.append(("Obelix", start.astimezone(UTC), (start + timedelta(days=4)).astimezone(UTC)))
        if is_sunday and service.congregation == "Gallisches Dorf":
            duties.append((service.slot_id, ORGANIST_NAME))
        if week == 4 and is_sunday and service.congregation == "Babaorum":
            duties.append((service.slot_id, "Automatix"))
        if leader is not None:
            leaders[service.slot_id] = leader
        if week <= 1:
            confirmed.add(service.slot_id)
    return DemoPlan(leaders, frozenset(confirmed), tuple(absences), tuple(duties))


async def _reset(session, district_id: uuid.UUID) -> None:
    """Remove the demo district; its congregations, slots and tokens follow by cascade."""
    await session.execute(
        text(
            "DELETE FROM memberships WHERE scope_id = :d OR scope_id IN "
            "(SELECT id FROM congregations WHERE district_id = :d)"
        ),
        {"d": district_id},
    )
    await session.execute(text("DELETE FROM districts WHERE id = :d"), {"d": district_id})


async def seed_demo_district(session, *, today: date, reset: bool = False) -> str | None:
    """Create the demo district once; ``reset`` recreates it for the current weeks.

    Returns the raw token of the new public calendar subscription (shown once, like the
    API does) or ``None`` when the district already existed.
    """
    district_repo = SqlDistrictRepository(session)
    existing = next(
        (d for d in await district_repo.list_all() if d.name == DEMO_DISTRICT_NAME), None
    )
    if existing is not None:
        if not reset:
            print(f"{DEMO_DISTRICT_NAME} existiert bereits (--reset-demo legt ihn neu an).")
            return None
        await _reset(session, existing.id)

    district = District.create(name=DEMO_DISTRICT_NAME, state_code=DEMO_STATE_CODE)
    await district_repo.save(district)
    congregation_repo = SqlCongregationRepository(session)
    congregations: dict[str, Congregation] = {}
    for name, service_times in DEMO_CONGREGATIONS.items():
        congregations[name] = Congregation.create(
            name=name, district_id=district.id, service_times=service_times
        )
        await congregation_repo.save(congregations[name])

    leader_repo = SqlLeaderRepository(session)
    leaders: dict[str, Leader] = {}
    for seed in DEMO_LEADERS:
        leaders[seed.name] = Leader.create(
            name=seed.name,
            district_id=district.id,
            rank=seed.rank,
            congregation_id=congregations[seed.congregation].id if seed.congregation else None,
            special_role=seed.role,
        )
        await leader_repo.save(leaders[seed.name])

    slot_repo = SqlPlanningSlotRepository(session)
    monday = today - timedelta(days=today.weekday())
    await GenerateDraftServicesUseCase(
        district_repo=district_repo,
        congregation_repo=congregation_repo,
        slot_repo=slot_repo,
        instance_repo=SqlEventInstanceRepository(session),
        timezone_name=DEMO_TIMEZONE,
    ).run_for_window(
        from_date=monday,
        to_date_exclusive=monday + timedelta(weeks=DEMO_WEEKS),
        district_ids={district.id},
    )
    for year in sorted({monday.year, (monday + timedelta(weeks=DEMO_WEEKS)).year}):
        await import_kirchliche_festtage(district.id, year, session)

    names = {c.id: c.name for c in congregations.values()}
    slots = [
        slot
        for slot in await slot_repo.list_for_date_range(
            district_id=district.id,
            from_date=monday - timedelta(days=1),
            to_date=monday + timedelta(weeks=DEMO_WEEKS),
        )
        if slot.category == "Gottesdienst" and slot.congregation_id in names
    ]
    services = [
        DemoService(
            slot.id,
            names[slot.congregation_id],
            datetime.combine(slot.planning_date, slot.planning_time, tzinfo=UTC),
        )
        for slot in slots
    ]
    plan = plan_demo(services, monday=monday)

    assignment_repo = SqlServiceAssignmentRepository(session)
    for slot in slots:
        released = slot.id in plan.confirmed
        slot.approval_status = (
            EventApprovalStatus.CONFIRMED if released else EventApprovalStatus.PLANNED
        )
        await slot_repo.save(slot)
        leader_name = plan.leaders.get(slot.id)
        if leader_name is not None:
            await assignment_repo.save(
                ServiceAssignment.create(
                    event_id=slot.id,
                    leader_id=leaders[leader_name].id,
                    leader_name=leader_name,
                    status=AssignmentStatus.CONFIRMED if released else AssignmentStatus.ASSIGNED,
                )
            )

    absence_repo = SqlLeaderUnavailabilityRepository(session)
    for leader_name, start_at, end_at in plan.absences:
        await absence_repo.save(
            LeaderUnavailability.create(
                leader_id=leaders[leader_name].id,
                start_at=start_at,
                end_at=end_at,
                reason=UnavailabilityReason.VACATION,
                note="Demo: Wildschweinjagd",
            )
        )

    duty_repo = SqlEventDutiesRepository(session)
    # A new district starts with the default duty catalogue (organist, conductor, closing).
    categories, _ = await duty_repo.catalog(district.id)
    organist = next((c for c in categories if c.code == "organist"), None)
    if organist is None:
        organist = next(c for c in EventDutyCategory.defaults(district.id) if c.code == "organist")
        organist = await duty_repo.save_category(organist)
    by_slot = {slot.id: slot for slot in slots}
    for slot_id, person in plan.organist_duties:
        leader = leaders.get(person)
        await duty_repo.save_assignment(
            EventDutyAssignment.create(
                slot_id,
                organist,
                by_slot[slot_id].congregation_id,
                name=None if leader else person,
                leader_id=leader.id if leader else None,
                leader_display_name=f"{leader.rank.value} {leader.name}" if leader else None,
            )
        )

    token, raw = ExportToken.create(
        label=DEMO_TOKEN_LABEL,
        token_type=TokenType.PUBLIC,
        district_id=district.id,
        congregation_id=None,
    )
    await SqlExportTokenRepository(session).save(token)
    print(
        f"{DEMO_DISTRICT_NAME}: {len(congregations)} Gemeinden, {len(leaders)} Amtsträger, "
        f"{len(slots)} Gottesdienste ({len(slots) - len(plan.leaders)} ohne Dienstleiter)."
    )
    return raw
