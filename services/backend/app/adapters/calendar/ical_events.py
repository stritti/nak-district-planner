"""Expand iCalendar VEVENTs into window-bounded occurrences (#465).

Shared by the ICS and CalDAV connectors. Recurring series (RRULE/RDATE with
EXDATE and RECURRENCE-ID overrides) are expanded with ``recurring-ical-events``
(LGPL-3.0-or-later, used unmodified as a library). Each occurrence of a series
is identified by UID + RECURRENCE-ID; non-recurring events keep their UID.
Floating times and all-day dates are local to the configured district timezone.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import recurring_ical_events
from icalendar import Calendar

from app.config import settings
from app.domain.models.raw_calendar_event import RawCalendarEvent, occurrence_key

# Fallback horizon when a caller does not bound the window (sync always does).
_UNBOUNDED_START = datetime(1970, 1, 1, tzinfo=UTC)
_UNBOUNDED_SPAN = timedelta(days=731)


def _local_zone() -> ZoneInfo:
    return ZoneInfo(settings.sync_default_timezone)


def to_utc(value, tz: ZoneInfo | None = None) -> datetime:
    """Normalize an iCalendar date/datetime (or property) to aware UTC."""
    raw = value.dt if hasattr(value, "dt") else value
    if not isinstance(raw, datetime):
        raw = datetime(raw.year, raw.month, raw.day)
    if raw.tzinfo is None:
        raw = raw.replace(tzinfo=tz or _local_zone())
    return raw.astimezone(UTC)


def content_hash(uid: str, start_at: datetime, end_at: datetime, title: str) -> str:
    payload = f"{uid}|{start_at.isoformat()}|{end_at.isoformat()}|{title}"
    return hashlib.sha256(payload.encode()).hexdigest()


def _recurring_uids(calendar: Calendar) -> set[str]:
    return {
        str(component.get("UID"))
        for component in calendar.walk("VEVENT")
        if any(name in component for name in ("RRULE", "RDATE", "RECURRENCE-ID"))
    }


def _recurrence_label(value: date | datetime, tz: ZoneInfo) -> str:
    if isinstance(value, datetime):
        return to_utc(value, tz).strftime("%Y%m%dT%H%M%SZ")
    return value.strftime("%Y%m%d")


def expand_events(
    calendar: Calendar,
    *,
    from_dt: datetime | None,
    to_dt: datetime | None,
    revision_marker: str | None = None,
    resource_id: str | None = None,
) -> list[RawCalendarEvent]:
    """Return every event occurrence overlapping [from_dt, to_dt]."""
    tz = _local_zone()
    start = from_dt or _UNBOUNDED_START
    end = to_dt or (from_dt or datetime.now(UTC)) + _UNBOUNDED_SPAN
    # A VEVENT without DTSTART cannot be placed in time (and breaks expansion).
    calendar.subcomponents = [
        c for c in calendar.subcomponents if c.name != "VEVENT" or "DTSTART" in c
    ]
    recurring = _recurring_uids(calendar)
    events: list[RawCalendarEvent] = []
    for component in recurring_ical_events.of(calendar).between(start, end):
        uid = str(component.get("UID") or "")
        if not uid:
            continue
        start_at = to_utc(component["DTSTART"], tz)
        if "DTEND" in component:
            end_at = to_utc(component["DTEND"], tz)
        elif "DURATION" in component:
            end_at = start_at + component["DURATION"].dt
        else:
            end_at = start_at
        if end_at <= start_at:
            end_at = start_at + timedelta(days=1)  # legacy default for events without an end
        if uid in recurring:
            uid = occurrence_key(uid, _recurrence_label(component["RECURRENCE-ID"].dt, tz))
        title = str(component.get("SUMMARY") or "") or "(kein Titel)"
        description = component.get("DESCRIPTION")
        events.append(
            RawCalendarEvent(
                uid=uid,
                title=title,
                start_at=start_at,
                end_at=end_at,
                description=str(description).strip() if description else None,
                content_hash=content_hash(uid, start_at, end_at, title),
                is_cancelled=str(component.get("STATUS", "")).upper() == "CANCELLED",
                revision_marker=revision_marker,
                resource_id=resource_id,
            )
        )
    return events
