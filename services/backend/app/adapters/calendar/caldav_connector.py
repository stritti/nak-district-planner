# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""CalDAV calendar connector.

Fetches events from a CalDAV server and converts them into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"url": "https://example.com/calendars/user/default/",
                     "username": "user", "password": "pass"}
or with bearer token: {"url": "...", "access_token": "token"}
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx
from icalendar import Calendar as ICalendar

from app.adapters.calendar.caldav_protocol import (
    build_calendar_query,
    collection_url,
    dav_auth,
    format_utc,
    parse_multistatus,
    resource_url,
)
from app.adapters.calendar.deletion import delete_resource
from app.adapters.calendar.http_policy import resilient_request
from app.adapters.calendar.ical_events import expand_events
from app.adapters.calendar.url_guard import guarded_client
from app.domain.models.raw_calendar_event import RawCalendarEvent, is_occurrence_key
from app.domain.ports.calendar import (
    CalendarConnector,
    CalendarConnectorError,
    OccurrenceWriteBackError,
)

logger = logging.getLogger(__name__)


def _refuse_occurrence_write(event: RawCalendarEvent) -> None:
    """A series is one resource: writing one occurrence would rewrite or delete all."""
    if event.recurrence_id is not None or is_occurrence_key(event.uid):
        raise OccurrenceWriteBackError()


class CalDAVConnector(CalendarConnector):
    """Adapter for CalDAV servers.

    DAV XML, hrefs and authentication are handled by ``caldav_protocol``;
    only idempotent REPORT/GET requests are retried.
    """

    authoritative_snapshot = True
    window_bounded_snapshot = True

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or guarded_client()

    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        collection = collection_url(credentials)
        auth = dav_auth(credentials)
        query = build_calendar_query(from_dt, to_dt)
        kwargs = auth.request_kwargs()
        kwargs["headers"].update({"Content-Type": "application/xml; charset=utf-8", "Depth": "1"})

        # Generic text on failure: no status/transport oracle, no URL or credentials (#463).
        response = await resilient_request(
            lambda: self._client.request("REPORT", collection, content=query, **kwargs),
            provider="CalDAV",
        )

        events: list[RawCalendarEvent] = []
        # A resource that is missing, empty or unparseable is skipped, but the
        # result then no longer proves deletions (snapshot_complete=False).
        unusable = 0
        for resource in parse_multistatus(response.content):
            try:
                cal = (
                    ICalendar.from_ical(resource.calendar_data)
                    if resource.calendar_data.strip()
                    else None
                )
            except Exception:
                cal = None
            if cal is None:
                unusable += 1
                continue

            try:
                expanded = expand_events(
                    cal,
                    from_dt=from_dt,
                    to_dt=to_dt,
                    revision_marker=resource.etag,
                    resource_id=resource.href,
                )
            except Exception as exc:
                # Fail the snapshot instead of silently dropping (and then
                # reconciling away) every occurrence of this resource.
                raise CalendarConnectorError("CalDAV Serie konnte nicht expandiert werden") from exc
            events.extend(expanded.events)
            unusable += not expanded.complete

        self.snapshot_complete = unusable == 0
        if unusable:
            # Count only: hrefs and payloads are provider-controlled.
            logger.warning("CalDAV snapshot incomplete: %d unusable resource(s)", unusable)
        return events

    async def update_event_times(
        self, credentials: dict, event: RawCalendarEvent, *, start_at: datetime, end_at: datetime
    ) -> str | None:
        """Update only event times while preserving the provider's current resource fields."""
        _refuse_occurrence_write(event)
        url = self._resource_url(credentials, event.resource_id)
        auth = dav_auth(credentials)

        try:
            current_response = await resilient_request(
                lambda: self._client.get(url, **auth.request_kwargs()), provider="CalDAV"
            )
        except CalendarConnectorError as exc:
            raise CalendarConnectorError(
                "CalDAV Kalender-Ressource konnte nicht geladen werden"
            ) from exc

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

        for prop in ("DTSTART", "DTEND", "DURATION"):
            if prop in component:
                del component[prop]
        component.add("dtstart", start_at)
        component.add("dtend", end_at)

        kwargs = auth.request_kwargs()
        kwargs["headers"]["Content-Type"] = "text/calendar; charset=utf-8"
        if event.revision_marker:
            kwargs["headers"]["If-Match"] = event.revision_marker
        elif current_etag := current_response.headers.get("etag"):
            # Explicit conflict resolution intentionally omits the stale revision.
            # Use the freshly fetched revision so remote soft fields are preserved
            # while still detecting a race between GET and PUT.
            kwargs["headers"]["If-Match"] = current_etag

        # PUT is not retried: a lost response would turn a retry into a 412.
        try:
            response = await self._client.put(url, content=calendar.to_ical(), **kwargs)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CalendarConnectorError("CalDAV Kalender-Aktualisierung fehlgeschlagen") from exc
        return response.headers.get("etag")

    async def delete_event(self, credentials: dict, event: RawCalendarEvent) -> None:
        _refuse_occurrence_write(event)
        url = self._resource_url(credentials, event.resource_id)
        kwargs = dav_auth(credentials).request_kwargs()
        if event.revision_marker:
            kwargs["headers"]["If-Match"] = event.revision_marker
        await delete_resource(self._client, url, **kwargs)

    async def resource_exists(self, credentials: dict, resource_id: str) -> bool:
        """GET the resource href; 404/410 means deleted, other failures raise."""
        url = self._resource_url(credentials, resource_id)
        try:
            response = await self._client.get(url, **dav_auth(credentials).request_kwargs())
            if response.status_code in (404, 410):
                return False
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CalendarConnectorError("CalDAV Ressource konnte nicht geprüft werden") from exc
        return True

    @staticmethod
    def _resource_url(credentials: dict, href: str | None) -> str:
        if not href:
            raise CalendarConnectorError("CalDAV resource href fehlt")
        return resource_url(collection_url(credentials), href)

    def _format_datetime(self, dt: datetime | None) -> str:
        """Format datetime for CalDAV time-range format."""
        return format_utc(dt) if dt is not None else ""
