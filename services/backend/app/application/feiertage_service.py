"""Feiertags-Import — zwei Quellen:

1. Nager.Date (öffentliche API): gesetzliche Feiertage pro Bundesland
2. Kirchliche Festtage (berechnet): NAK-relevante bewegliche Festtage aus dem Ostertermin

Idempotent: UIDs sind stabil — wiederholter Import überschreibt nur bei Änderungen.

NOTE: Since matrix rendering migration (Task Group 1.1), holidays are now stored as
PlanningSlots instead of Events to support the unified PlanningSlot/EventInstance architecture.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, date, datetime, time, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus

NAGER_DATE_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/DE"

DE_STATES: dict[str, str] = {
    "BB": "Brandenburg",
    "BE": "Berlin",
    "BW": "Baden-Württemberg",
    "BY": "Bayern",
    "HB": "Bremen",
    "HE": "Hessen",
    "HH": "Hamburg",
    "MV": "Mecklenburg-Vorpommern",
    "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "SH": "Schleswig-Holstein",
    "SL": "Saarland",
    "SN": "Sachsen",
    "ST": "Sachsen-Anhalt",
    "TH": "Thüringen",
}


# ── Kirchliche Festtage (NAK) ─────────────────────────────────────────────────
# (name, offset in days from Easter Sunday)
KIRCHLICHE_FESTTAGE: list[tuple[str, int]] = [
    ("Palmsonntag", -7),
    ("Ostersonntag", 0),
    ("Pfingstsonntag", 49),
]

# Entschlafenen-Gottesdienste: jeweils erster Sonntag im März, Juli, November
ENTSCHLAFENEN_MONATE: list[tuple[str, int]] = [
    ("Entschlafenen-Gottesdienst", 3),
    ("Entschlafenen-Gottesdienst", 7),
    ("Entschlafenen-Gottesdienst", 11),
]


def _first_sunday(year: int, month: int) -> date:
    """Return the first Sunday of the given month/year."""
    d = date(year, month, 1)
    days_until_sunday = (6 - d.weekday()) % 7
    return d + timedelta(days=days_until_sunday)


def _easter_sunday(year: int) -> date:
    """Compute Easter Sunday (Gregorian calendar) via the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month = (h + ll - 7 * m + 114) // 31
    day = (h + ll - 7 * m + 114) % 31 + 1
    return date(year, month, day)


# ── Shared helpers ────────────────────────────────────────────────────────────


def _content_hash(date: str, name: str) -> str:
    return hashlib.sha256(f"{date}|{name}".encode()).hexdigest()


def _external_uid(district_id: uuid.UUID, date: str, name: str) -> str:
    slug = (
        name.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
    )
    return f"feiertag-DE-{district_id}-{date}-{slug}"


def _parse_day(date_str: str) -> tuple[datetime, datetime]:
    y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:])
    start = datetime(y, m, d, 0, 0, 0, tzinfo=UTC)
    end = datetime(y, m, d, 23, 59, 59, tzinfo=UTC)
    return start, end


async def import_feiertage(
    district_id: uuid.UUID,
    year: int,
    state_code: str | None,
    session: AsyncSession,
) -> dict[str, int]:
    """Fetch German public holidays from Nager.Date and upsert as district PlanningSlots.

    Args:
        district_id: Target district.
        year: Calendar year (e.g. 2025).
        state_code: 2-letter German state code (e.g. "BY") or None for national only.
        session: Active DB session.

    Returns:
        dict with created/updated/skipped counts.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(NAGER_DATE_URL.format(year=year))
        resp.raise_for_status()
        holidays: list[dict] = resp.json()

    de_county = f"DE-{state_code}" if state_code else None

    # Include national holidays (counties=None) and state-specific ones matching state_code
    relevant = [
        h
        for h in holidays
        if h.get("counties") is None or (de_county and de_county in (h.get("counties") or []))
    ]

    slot_repo = SqlPlanningSlotRepository(session)
    created = updated = skipped = 0

    for h in relevant:
        date_str: str = h["date"]
        name: str = h["localName"]
        chash = _content_hash(date_str, name)
        holiday_date = date.fromisoformat(date_str)
        # For holidays, use midnight as the planning time
        planning_time = time(0, 0, 0)

        # Check if a PlanningSlot for this holiday already exists
        # We query by district, date, and category to find existing holiday slots
        existing_slots = await slot_repo.list_for_date_range(
            district_id=district_id,
            from_date=holiday_date,
            to_date=holiday_date,
        )
        existing = None
        for slot in existing_slots:
            if slot.category == "Feiertag" and slot.title == name:
                existing = slot
                break

        if existing is None:
            # Create new PlanningSlot for the holiday
            slot = PlanningSlot.create(
                district_id=district_id,
                planning_date=holiday_date,
                planning_time=planning_time,
                category="Feiertag",
                title=name,
                status=PlanningSlotStatus.ACTIVE,
            )
            await slot_repo.save(slot)
            created += 1
        elif existing.title != name or existing.planning_date != holiday_date:
            # Update existing slot
            existing.title = name
            existing.planning_date = holiday_date
            existing.updated_at = datetime.now(UTC)
            await slot_repo.save(existing)
            updated += 1
        else:
            skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped}


async def import_kirchliche_festtage(
    district_id: uuid.UUID,
    year: int,
    session: AsyncSession,
) -> dict[str, int]:
    """Import NAK-relevant computed dates:
    - Kirchliche Festtage: Palmsonntag, Ostersonntag, Pfingstsonntag (aus Ostern abgeleitet)
    - Entschlafenen-Gottesdienste: erster Sonntag im März, Juli und November

    No external API call — purely computed.  Applies to all districts regardless of state_code.
    
    NOTE: Creates PlanningSlots instead of Events for matrix rendering compatibility.
    """
    easter = _easter_sunday(year)
    slot_repo = SqlPlanningSlotRepository(session)
    created = updated = skipped = 0

    festtage: list[tuple[str, date]] = []
    for name, offset in KIRCHLICHE_FESTTAGE:
        festtage.append((name, easter + timedelta(days=offset)))
    for name, month in ENTSCHLAFENEN_MONATE:
        festtage.append((name, _first_sunday(year, month)))

    for name, day in festtage:
        date_str = day.isoformat()
        chash = _content_hash(date_str, name)
        # For church holidays, use the actual date's time (midnight for all-day)
        planning_time = time(0, 0, 0)

        # Check if a PlanningSlot for this holiday already exists
        existing_slots = await slot_repo.list_for_date_range(
            district_id=district_id,
            from_date=day,
            to_date=day,
        )
        existing = None
        for slot in existing_slots:
            if slot.category == "Feiertag" and slot.title == name:
                existing = slot
                break

        if existing is None:
            # Create new PlanningSlot for the church holiday
            slot = PlanningSlot.create(
                district_id=district_id,
                planning_date=day,
                planning_time=planning_time,
                category="Feiertag",
                title=name,
                status=PlanningSlotStatus.ACTIVE,
            )
            await slot_repo.save(slot)
            created += 1
        elif existing.title != name or existing.planning_date != day:
            # Update existing slot
            existing.title = name
            existing.planning_date = day
            existing.updated_at = datetime.now(UTC)
            await slot_repo.save(existing)
            updated += 1
        else:
            skipped += 1

    return {"created": created, "updated": updated, "skipped": skipped}


async def reference_feiertage_for_congregation(
    district_id: uuid.UUID,
    congregation_id: uuid.UUID,
    session: AsyncSession,
) -> int:
    """Reference all district holiday PlanningSlots for a congregation.

    Adds the congregation ID to `applicability` for district-level Feiertag PlanningSlots.
    Existing references are kept untouched.

    Returns:
        Number of slots that were updated.
    """
    slot_repo = SqlPlanningSlotRepository(session)
    # Get all slots for the district (we need to fetch a reasonable date range)
    # For holidays, we typically look at a year's worth of data
    from_date = date(datetime.now(UTC).year - 1, 1, 1)
    to_date = date(datetime.now(UTC).year + 2, 12, 31)
    
    slots = await slot_repo.list_for_date_range(
        district_id=district_id,
        from_date=from_date,
        to_date=to_date,
    )

    updated = 0
    for slot in slots:
        if slot.category != "Feiertag":
            continue
        # District-level holidays have no congregation_id
        if slot.congregation_id is not None:
            continue
        if congregation_id in slot.applicability:
            continue
        slot.applicability = [*slot.applicability, congregation_id]
        slot.updated_at = datetime.now(UTC)
        await slot_repo.save(slot)
        updated += 1

    return updated
