"""CalDAV calendar connector.

Fetches events from a CalDAV server and converts them into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"url": "https://example.com/calendars/user/default/",
                     "username": "user", "password": "pass"}
or with bearer token: {"url": "...", "access_token": "token"}
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urljoin, urlsplit

import defusedxml.ElementTree as ET
import httpx
from icalendar import Calendar as ICalendar

from app.adapters.calendar.deletion import delete_resource
from app.adapters.calendar.ical_events import expand_events
from app.domain.models.raw_calendar_event import RawCalendarEvent, series_uid_of
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError


def _refuse_occurrence_write(event: RawCalendarEvent) -> None:
    """A series is one resource: writing one occurrence would rewrite or delete all."""
    if series_uid_of(event.uid) is not None:
        raise CalendarConnectorError(
            "Einzeltermine wiederkehrender CalDAV-Serien können nicht zurückgeschrieben werden"
        )


class CalDAVConnector(CalendarConnector):
    """Adapter for CalDAV servers."""

    authoritative_snapshot = True

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        url_value = credentials.get("url")
        if not url_value:
            raise CalendarConnectorError("CalDAV Basis-URL fehlt in den Credentials")
        url: str = str(url_value).rstrip("/")

        # Determine authentication method
        headers = {}
        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        elif not ("username" in credentials and "password" in credentials):
            raise CalendarConnectorError(
                "CalDAV credentials must include either access_token or username/password"
            )

        # Build CalDAV calendar-query REPORT for VEVENTs overlapping the window.
        # RFC 4791 9.9: unset bounds are omitted, never sent as empty attributes.
        bounds = " ".join(
            f'{name}="{self._format_datetime(value)}"'
            for name, value in (("start", from_dt), ("end", to_dt))
            if value is not None
        )
        time_range = f"\n                <C:time-range {bounds}/>" if bounds else ""
        calendar_query = f"""<?xml version="1.0" encoding="UTF-8"?>
<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
    <D:prop>
        <D:getetag/>
        <C:calendar-data/>
    </D:prop>
    <C:filter>
        <C:comp-filter name="VCALENDAR">
            <C:comp-filter name="VEVENT">{time_range}
            </C:comp-filter>
        </C:comp-filter>
    </C:filter>
</C:calendar-query>"""

        # Use the calendar-multiget REPORT if we know the hrefs, otherwise use calendar-query
        # For simplicity, we'll use calendar-query on the calendar collection itself
        report_url = f"{url}" if url.endswith("/") else f"{url}/"

        try:
            response = await self._client.request(
                "REPORT",
                report_url,
                data=calendar_query.encode("utf-8"),  # type: ignore[arg-type]
                headers={"Content-Type": "application/xml; charset=utf-8", "Depth": "1", **headers},
                auth=(str(credentials["username"]), str(credentials["password"]))
                if "username" in credentials and "password" in credentials
                else None,
            )
        except httpx.RequestError as exc:
            raise CalendarConnectorError("Transportfehler beim Laden des CalDAV Kalenders") from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise CalendarConnectorError(
                f"HTTP {exc.response.status_code} beim Laden des CalDAV Kalenders: {exc}"
            ) from exc

        # Parse the multi-status response
        # This is simplified - a production implementation would properly parse XML
        # For now, we'll look for calendar-data elements
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            raise CalendarConnectorError(f"Ungültige XML-Antwort vom CalDAV Server: {exc}") from exc

        # Define namespaces
        namespaces = {
            "D": "DAV:",
            "C": "urn:ietf:params:xml:ns:caldav",
            "ical": "http://apple.com/ns/ical/",
        }

        events: list[RawCalendarEvent] = []

        # Find all response elements
        for resp in root.findall(".//D:response", namespaces):
            # Get calendar-data element
            cal_data_elem = resp.find(".//C:calendar-data", namespaces)
            if cal_data_elem is None or cal_data_elem.text is None:
                continue

            cal_data = cal_data_elem.text
            if not cal_data.strip():
                continue

            # Parse the iCalendar data
            try:
                cal = ICalendar.from_ical(cal_data)
            except Exception:
                # Skip invalid iCalendar data
                continue

            try:
                events.extend(
                    expand_events(
                        cal,
                        from_dt=from_dt,
                        to_dt=to_dt,
                        revision_marker=resp.findtext("D:getetag", namespaces=namespaces)
                        or resp.findtext(".//D:getetag", namespaces=namespaces),
                        resource_id=resp.findtext("D:href", namespaces=namespaces),
                    )
                )
            except Exception as exc:
                # Fail the snapshot instead of silently dropping (and then
                # reconciling away) every occurrence of this resource.
                raise CalendarConnectorError("CalDAV Serie konnte nicht expandiert werden") from exc

        return events

    async def update_event_times(
        self, credentials: dict, event: RawCalendarEvent, *, start_at: datetime, end_at: datetime
    ) -> str | None:
        """Update only event times while preserving the provider's current resource fields."""
        _refuse_occurrence_write(event)
        if not event.resource_id or "url" not in credentials:
            raise CalendarConnectorError("CalDAV resource href oder Basis-URL fehlt")
        base = credentials["url"].rstrip("/") + "/"
        url = urljoin(base, event.resource_id)
        source, target = urlsplit(base), urlsplit(url)
        if (source.scheme, source.netloc) != (target.scheme, target.netloc) or not target.path.startswith(source.path):
            raise CalendarConnectorError("CalDAV resource liegt außerhalb des Kalenders")

        auth = (
            (credentials["username"], credentials["password"])
            if "username" in credentials and "password" in credentials
            else None
        )
        request_headers: dict[str, str] = {}
        if "access_token" in credentials:
            request_headers["Authorization"] = f"Bearer {credentials['access_token']}"
        elif auth is None:
            raise CalendarConnectorError("CalDAV Credentials fehlen")

        try:
            current_response = await self._client.get(
                url,
                headers=request_headers,
                auth=auth,
            )
            current_response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CalendarConnectorError("CalDAV Kalender-Ressource konnte nicht geladen werden") from exc

        try:
            calendar = ICalendar.from_ical(current_response.content)
        except Exception as exc:
            raise CalendarConnectorError("Ungültige CalDAV Kalender-Ressource") from exc

        component = next(
            (
                candidate
                for candidate in calendar.walk()
                if candidate.name == "VEVENT" and str(candidate.get("UID", "")) == event.uid
            ),
            None,
        )
        if component is None:
            raise CalendarConnectorError("CalDAV Ereignis wurde in der Ressource nicht gefunden")

        if "DTSTART" in component:
            del component["DTSTART"]
        if "DTEND" in component:
            del component["DTEND"]
        if "DURATION" in component:
            del component["DURATION"]
        component.add("dtstart", start_at)
        component.add("dtend", end_at)

        headers = {"Content-Type": "text/calendar; charset=utf-8", **request_headers}
        if event.revision_marker:
            headers["If-Match"] = event.revision_marker
        elif current_etag := current_response.headers.get("etag"):
            # Explicit conflict resolution intentionally omits the stale revision.
            # Use the freshly fetched revision so remote soft fields are preserved
            # while still detecting a race between GET and PUT.
            headers["If-Match"] = current_etag

        try:
            response = await self._client.put(
                url,
                content=calendar.to_ical(),
                headers=headers,
                auth=auth,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CalendarConnectorError("CalDAV Kalender-Aktualisierung fehlgeschlagen") from exc
        return response.headers.get("etag")

    async def delete_event(self, credentials: dict, event: RawCalendarEvent) -> None:
        _refuse_occurrence_write(event)
        if not event.resource_id:
            raise CalendarConnectorError("CalDAV resource href fehlt")
        if "url" not in credentials:
            raise CalendarConnectorError("CalDAV Basis-URL fehlt in den Credentials")
        base = credentials["url"].rstrip("/") + "/"
        url = urljoin(base, event.resource_id)
        source, target = urlsplit(base), urlsplit(url)
        if (source.scheme, source.netloc) != (target.scheme, target.netloc) or not target.path.startswith(source.path):
            raise CalendarConnectorError("CalDAV resource liegt außerhalb des Kalenders")
        headers = {}
        if event.revision_marker:
            headers["If-Match"] = event.revision_marker
        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        await delete_resource(
            self._client, url, headers=headers,
            auth=(credentials["username"], credentials["password"]) if "username" in credentials else None,
        )

    def _format_datetime(self, dt: datetime | None) -> str:
        """Format datetime for CalDAV time-range format."""
        if dt is None:
            return ""
        # CalDAV expects format like: 20230101T000000Z
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        else:
            dt = dt.astimezone(UTC)
        return dt.strftime("%Y%m%dT%H%M%SZ")
