"""Read-only iCal/ICS calendar connector.

Fetches an ICS feed via HTTP and converts VEVENT components into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"url": "https://example.com/feed.ics"}
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone

import httpx
from icalendar import Calendar as ICalendar  # type: ignore[import-untyped]

from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector


def _to_utc(dt: datetime | date) -> datetime:
    """Convert a date or datetime to a timezone-aware UTC datetime."""
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    # All-day event: treat as midnight UTC
    return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)


def _content_hash(uid: str, start_at: datetime, end_at: datetime, title: str) -> str:
    payload = f"{uid}|{start_at.isoformat()}|{end_at.isoformat()}|{title}"
    return hashlib.sha256(payload.encode()).hexdigest()


class ICalConnector(CalendarConnector):
    """Read-only adapter for ICS/iCal feeds."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        url: str = credentials["url"]
        response = await self._client.get(url)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"HTTP {exc.response.status_code} beim Laden des Kalenders: {url}"
            ) from exc

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            raise ValueError(
                f"URL liefert HTML statt eines Kalenders (Content-Type: {content_type}). "
                "Bitte die direkte .ics-URL verwenden."
            )

        try:
            cal = ICalendar.from_ical(response.content)
        except Exception as exc:
            raise ValueError(f"Ungültiges iCal-Format: {exc}") from exc
        events: list[RawCalendarEvent] = []

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            uid_raw = component.get("UID")
            uid = str(uid_raw) if uid_raw else ""
            if not uid:
                continue  # skip events without a stable UID

            summary = component.get("SUMMARY", "")
            title = str(summary) if summary else "(kein Titel)"

            dtstart = component.get("DTSTART")
            dtend = component.get("DTEND")
            duration = component.get("DURATION")

            if dtstart is None:
                continue  # skip events without a start time

            start_at = _to_utc(dtstart.dt)

            if dtend is not None:
                end_at = _to_utc(dtend.dt)
            elif duration is not None:
                end_at = start_at + duration.dt
            else:
                # All-day default: 1 day
                end_at = start_at + timedelta(days=1)

            description_raw = component.get("DESCRIPTION")
            description = str(description_raw).strip() if description_raw else None

            status_raw = component.get("STATUS")
            is_cancelled = str(status_raw).upper() == "CANCELLED" if status_raw else False

            # Optional client-side time-window filtering
            if from_dt is not None and end_at < from_dt:
                continue
            if to_dt is not None and start_at > to_dt:
                continue

            events.append(
                RawCalendarEvent(
                    uid=uid,
                    title=title,
                    start_at=start_at,
                    end_at=end_at,
                    description=description,
                    content_hash=_content_hash(uid, start_at, end_at, title),
                    is_cancelled=is_cancelled,
                )
            )

        return events
