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

import httpx

from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector


def _content_hash(uid: str, start_at: datetime, end_at: datetime, title: str) -> str:
    payload = f"{uid}|{start_at.isoformat()}|{end_at.isoformat()}|{title}"
    return hashlib.sha256(payload.encode()).hexdigest()


class CalDAVConnector(CalendarConnector):
    """Adapter for CalDAV servers."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        url: str = credentials["url"].rstrip("/")

        # Determine authentication method
        headers = {}
        if "access_token" in credentials:
            headers["Authorization"] = f"Bearer {credentials['access_token']}"
        elif "username" in credentials and "password" in credentials:
            # Basic auth will be handled by httpx if we pass username/password to client
            pass
        else:
            raise ValueError(
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

        response = await self._client.request(
            "REPORT",
            report_url,
            data=calendar_query.encode("utf-8"),
            headers={"Content-Type": "application/xml; charset=utf-8", "Depth": "1", **headers},
            auth=(credentials.get("username"), credentials.get("password"))
            if "username" in credentials and "password" in credentials
            else None,
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"HTTP {exc.response.status_code} beim Laden des CalDAV Kalenders: {exc}"
            ) from exc

        # Parse the multi-status response
        # This is simplified - a production implementation would properly parse XML
        # For now, we'll look for calendar-data elements
        import defusedxml.ElementTree as ET

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            raise ValueError(f"Ungültige XML-Antwort vom CalDAV Server: {exc}") from exc

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
                from icalendar import Calendar as ICalendar

                cal = ICalendar.from_ical(cal_data.encode("utf-8"))
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

                # Convert to UTC datetime
                def _to_utc(dt):
                    if hasattr(dt, "dt"):
                        dt_val = dt.dt
                    else:
                        dt_val = dt

                    if isinstance(dt_val, datetime):
                        if dt_val.tzinfo is None:
                            return dt_val.replace(tzinfo=UTC)
                        return dt_val.astimezone(UTC)
                    else:  # date object
                        return datetime(dt_val.year, dt_val.month, dt_val.day, tzinfo=UTC)

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
                    )
                )

        return events

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
