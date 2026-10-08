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
from typing import NamedTuple
from zoneinfo import ZoneInfo

import recurring_ical_events
from dateutil.rrule import rrulestr
from icalendar import Calendar, vRecur

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


class RecurrenceLimitError(ValueError):
    """A feed would expand into more work than one sync may spend on it."""

    def __init__(self) -> None:
        super().__init__("Kalender enthält zu viele oder zu dichte Serientermine")


_SUB_DAILY = {"SECONDLY", "MINUTELY", "HOURLY"}
# dateutil steps (from each series' DTSTART up to the window end) per feed.
_ITERATION_BUDGET = 100_000


def _naive(value: date | datetime) -> datetime:
    if not isinstance(value, datetime):
        return datetime(value.year, value.month, value.day)
    return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value


def _guard_recurrences(calendar: Calendar, start: datetime, end: datetime) -> None:
    """Bound expansion cost before the library materializes occurrences.

    External feeds are untrusted: sub-daily rules are rejected, iteration from
    each DTSTART is budgeted and in-window occurrences are capped, so a hostile
    RRULE fails the sync quickly instead of exhausting CPU and memory.
    """
    budget, in_window = _ITERATION_BUDGET, 0
    window_start, window_end = _naive(start), _naive(end)
    for component in calendar.walk("VEVENT"):
        rules = component.get("RRULE") or []
        for rule in rules if isinstance(rules, list) else [rules]:
            if str((rule.get("FREQ") or [""])[0]).upper() in _SUB_DAILY:
                raise RecurrenceLimitError()
            # dateutil needs DTSTART and UNTIL in the same form: both naive UTC.
            params = dict(rule)
            if params.get("UNTIL"):
                params["UNTIL"] = [_naive(params["UNTIL"][0])]
            dtstart = _naive(component["DTSTART"].dt)
            for occurrence in rrulestr(vRecur(params).to_ical().decode(), dtstart=dtstart):
                budget -= 1
                if occurrence > window_end:
                    break
                in_window += occurrence >= window_start
                if budget < 0 or in_window > settings.sync_max_occurrences:
                    raise RecurrenceLimitError()


# Marks source VEVENTs without DTEND and DURATION; the expansion library copies
# it into every occurrence (it fills in DTEND itself, hiding the difference).
_OPEN_END = "X-NAK-OPEN-END"


def _raw_event(component, key: str, tz: ZoneInfo, **extra) -> RawCalendarEvent:
    start_at = to_utc(component["DTSTART"], tz)
    if component.get(_OPEN_END):
        end_at = start_at + timedelta(days=1)  # legacy default for events without an end
    elif "DTEND" in component:
        end_at = to_utc(component["DTEND"], tz)
    elif "DURATION" in component:
        end_at = start_at + component["DURATION"].dt
    else:
        end_at = start_at
    title = str(component.get("SUMMARY") or "") or "(kein Titel)"
    description = component.get("DESCRIPTION")
    return RawCalendarEvent(
        uid=key,
        title=title,
        start_at=start_at,
        end_at=end_at,
        description=str(description).strip() if description else None,
        content_hash=content_hash(key, start_at, end_at, title),
        is_cancelled=str(component.get("STATUS", "")).upper() == "CANCELLED",
        **extra,
    )


def _identity(component, recurring: set[str], tz: ZoneInfo) -> tuple[str, dict]:
    uid = str(component.get("UID"))
    if uid not in recurring:
        return uid, {}
    recurrence_id = _recurrence_label(component["RECURRENCE-ID"].dt, tz)
    return occurrence_key(uid, recurrence_id), {"series_uid": uid, "recurrence_id": recurrence_id}


class ExpandedCalendar(NamedTuple):
    events: list[RawCalendarEvent]
    # False when a VEVENT had to be dropped (broken property, no DTSTART):
    # its absence must not be mistaken for a deletion at the source.
    complete: bool


def _usable(component) -> bool:
    return "DTSTART" in component and not getattr(component, "errors", None)


def expand_events(
    calendar: Calendar,
    *,
    from_dt: datetime | None,
    to_dt: datetime | None,
    revision_marker: str | None = None,
    resource_id: str | None = None,
) -> ExpandedCalendar:
    """Return every occurrence overlapping [from_dt, to_dt], plus presence markers.

    Single events and RECURRENCE-ID overrides outside the window are returned
    with ``outside_window=True``: they still exist at the source (e.g. moved
    beyond the window) and must not be reconciled as deleted. Generated
    occurrences outside the window are not materialized.
    """
    tz = _local_zone()
    start = from_dt or _UNBOUNDED_START
    end = to_dt or (from_dt or datetime.now(UTC)) + _UNBOUNDED_SPAN
    # A VEVENT without UID can never have been linked and is ignored. One that
    # is broken or lacks DTSTART is dropped and makes the snapshot incomplete.
    vevents = [c for c in calendar.subcomponents if c.name == "VEVENT" and c.get("UID")]
    usable = [c for c in vevents if _usable(c)]
    complete = len(usable) == len(vevents)
    calendar.subcomponents = [c for c in calendar.subcomponents if c.name != "VEVENT"] + usable
    for component in usable:
        if "DTEND" not in component and "DURATION" not in component:
            component[_OPEN_END] = "1"
    _guard_recurrences(calendar, start, end)
    recurring = _recurring_uids(calendar)
    source = {"revision_marker": revision_marker, "resource_id": resource_id}
    events: list[RawCalendarEvent] = []
    for component in recurring_ical_events.of(calendar).between(start, end):
        key, identity = _identity(component, recurring, tz)
        events.append(_raw_event(component, key, tz, **identity, **source))
    if len(events) > settings.sync_max_occurrences:
        raise RecurrenceLimitError()
    seen = {event.uid for event in events}
    for component in calendar.walk("VEVENT"):
        if any(name in component for name in ("RRULE", "RDATE")):
            continue  # series masters: occurrences outside the window stay virtual
        key, identity = _identity(component, recurring, tz)
        if key not in seen:
            seen.add(key)
            events.append(_raw_event(component, key, tz, outside_window=True, **identity, **source))
    return ExpandedCalendar(events, complete)
