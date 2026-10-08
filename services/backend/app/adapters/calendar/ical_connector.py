"""Read-only iCal/ICS calendar connector.

Fetches an ICS feed via HTTP and converts VEVENT components into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"url": "https://example.com/feed.ics"}
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
from icalendar import Calendar as ICalendar  # type: ignore[import-untyped]

from app.adapters.calendar.http_policy import resilient_request
from app.adapters.calendar.ical_events import expand_events
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError

logger = logging.getLogger(__name__)


class ICalConnector(CalendarConnector):
    """Read-only adapter for ICS/iCal feeds.

    A feed is a complete snapshot: within the queried window, an event that
    disappeared from the feed was removed at the source.
    """

    authoritative_snapshot = True

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        url_value = credentials.get("url")
        if not url_value:
            raise CalendarConnectorError("iCal URL fehlt")
        url = str(url_value)
        response = await resilient_request(
            lambda: self._client.get(url), provider="iCal"
        )

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            raise CalendarConnectorError(
                f"URL liefert HTML statt eines Kalenders (Content-Type: {content_type}). "
                "Bitte die direkte .ics-URL verwenden."
            )

        try:
            cal = ICalendar.from_ical(response.content.decode("utf-8"))
            expanded = expand_events(cal, from_dt=from_dt, to_dt=to_dt)
        except Exception as exc:
            raise CalendarConnectorError(f"Ungültiges iCal-Format: {exc}") from exc
        self.snapshot_complete = expanded.complete
        if not expanded.complete:
            logger.warning("iCal feed contains unparseable events; snapshot is incomplete")
        return expanded.events
