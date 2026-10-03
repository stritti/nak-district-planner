"""CalDAV calendar connector.

Fetches events from a CalDAV server and converts them into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"url": "https://example.com/calendars/user/default/",
                     "username": "user", "password": "pass"}
or with bearer token: {"url": "...", "access_token": "token"}
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin, urlsplit

import defusedxml.ElementTree as ET
import httpx
from icalendar import Calendar as ICalendar
from icalendar import Event as ICalendarEvent

from app.adapters.calendar.deletion import delete_resource
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError


def _content_hash(uid: str, start_at: datetime, end_at: datetime, title: str) -> str:
    payload = f"{uid}|{start_at.isoformat()}|{end_at.isoformat()}|{title}"
    return hashlib.sha256(payload.encode()).hexdigest()



def _to_utc(value) -> datetime:
    """Normalize iCalendar date/datetime values to UTC."""
    raw = value.dt if hasattr(value, "dt") else value
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=UTC) if raw.tzinfo is None else raw.astimezone(UTC)
    return datetime(raw.year, raw.month, raw.day, tzinfo=UTC)


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

        # Build CalDAV calendar-query REPORT
        # This requests VEVENT components in the specified time range
        calendar_query = f"""<?xml version="1.0" encoding="UTF-8"?>
<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
    <D:prop>
        <D:getetag/>
        <C:calendar-data/>
    </D:prop>
    <C:filter>
        <C:comp-filter name="VCALENDAR">
            <C:comp-filter name="VEVENT">
                <C:time-range start="{self._format_datetime(from_dt) if from_dt else ""}" 
                             end="{self._format_datetime(to_dt) if to_dt else ""}"/>
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

            # Extract VEVENT components
            for component in cal.walk():
                if component.name != "VEVENT":
                    continue

                uid_raw = component.get("UID")
                uid = str(uid_raw) if uid_raw else ""
                if not uid:
                    continue

                summary = component.get("SUMMARY", "")
                title = str(summary) if summary else "(kein Titel)"

                dtstart = component.get("DTSTART")
                dtend = component.get("DTEND")
                duration = component.get("DURATION")

                if dtstart is None:
                    continue

                start_at = _to_utc(dtstart)

                if dtend is not None:
                    end_at = _to_utc(dtend)
                elif duration is not None:
                    end_at = start_at + duration.dt
                else:
                    # All-day default: 1 day
                    end_at = start_at + timedelta(days=1)

                description_raw = component.get("DESCRIPTION")
                description = str(description_raw).strip() if description_raw else None

                status_raw = component.get("STATUS")
                is_cancelled = str(status_raw).upper() == "CANCELLED" if status_raw else False

                events.append(
                    RawCalendarEvent(
                        uid=uid,
                        title=title,
                        start_at=start_at,
                        end_at=end_at,
                        description=description,
                        content_hash=_content_hash(uid, start_at, end_at, title),
                        is_cancelled=is_cancelled,
                        revision_marker=resp.findtext("D:getetag", namespaces=namespaces)
                        or resp.findtext(".//D:getetag", namespaces=namespaces),
                        resource_id=resp.findtext("D:href", namespaces=namespaces),
                    )
                )

        return events

    async def update_event_times(
        self, credentials: dict, event: RawCalendarEvent, *, start_at: datetime, end_at: datetime
    ) -> str | None:
        if not event.resource_id or "url" not in credentials:
            raise CalendarConnectorError("CalDAV resource href oder Basis-URL fehlt")
        base = credentials["url"].rstrip("/") + "/"
        url = urljoin(base, event.resource_id)
        source, target = urlsplit(base), urlsplit(url)
        if (source.scheme, source.netloc) != (target.scheme, target.netloc) or not target.path.startswith(source.path):
            raise CalendarConnectorError("CalDAV resource liegt außerhalb des Kalenders")
        headers = {"Content-Type": "text/calendar; charset=utf-8"}
        if event.revision_marker:
            headers["If-Match"] = event.revision_marker
        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        elif not ("username" in credentials and "password" in credentials):
            raise CalendarConnectorError("CalDAV Credentials fehlen")
        calendar = ICalendar()
        calendar.add("prodid", "-//NAK District Planner//Calendar Sync//")
        calendar.add("version", "2.0")
        component = ICalendarEvent()
        component.add("uid", event.uid)
        component.add("summary", event.title)
        component.add("dtstart", start_at)
        component.add("dtend", end_at)
        if event.description:
            component.add("description", event.description)
        calendar.add_component(component)
        try:
            response = await self._client.put(
                url,
                content=calendar.to_ical(),
                headers=headers,
                auth=(credentials["username"], credentials["password"])
                if "username" in credentials and "password" in credentials
                else None,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CalendarConnectorError("CalDAV Kalender-Aktualisierung fehlgeschlagen") from exc
        return response.headers.get("etag")

    async def delete_event(self, credentials: dict, event: RawCalendarEvent) -> None:
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
