# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Google Calendar connector.

Fetches events from Google Calendar API and converts them into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"access_token": "ya29.a0AfH6SMB..."}
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.adapters.calendar.bounded_http import make_bounded_client
from app.adapters.calendar.deletion import delete_resource
from app.adapters.calendar.http_policy import resilient_request
from app.adapters.calendar.pagination_budget import PaginationBudget
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError


class GoogleCalendarConnector(CalendarConnector):
    """Adapter for Google Calendar API."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        budget_factory: Callable[[], PaginationBudget] = PaginationBudget.from_settings,
    ) -> None:
        self._client = client or make_bounded_client()
        self._budget_factory = budget_factory

    async def _fetch_pages(
        self,
        url: str,
        params: dict[str, Any],
        headers: dict[str, str],
        budget: PaginationBudget,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            page_params = dict(params)
            if page_token:
                page_params["pageToken"] = page_token
            response = await resilient_request(
                lambda params=page_params: self._client.get(url, params=params, headers=headers),
                provider="Google",
            )
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                raise CalendarConnectorError(
                    f"URL liefert HTML statt eines Kalenders (Content-Type: {content_type}). "
                    "Bitte die direkte .ics-URL verwenden."
                )
            data = response.json()
            page_items = data.get("items", [])
            page_token = data.get("nextPageToken")
            budget.charge(
                items=len(page_items), size_bytes=len(response.content), next_token=page_token
            )
            items.extend(page_items)
            if not page_token:
                return items

    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        access_token = credentials.get("access_token")
        if not access_token:
            raise CalendarConnectorError("Google access_token fehlt")
        # Use primary calendar; could be made configurable
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

        params: dict[str, Any] = {
            "showDeleted": True,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if from_dt is not None:
            params["timeMin"] = from_dt.isoformat()
        if to_dt is not None:
            params["timeMax"] = to_dt.isoformat()

        headers = {"Authorization": f"Bearer {access_token}"}

        budget = self._budget_factory()
        items = await budget.run(self._fetch_pages(url, params, headers, budget))

        events: list[RawCalendarEvent] = []
        for item in items:
            uid = item.get("id", "")
            if not uid:
                continue

            summary = item.get("summary", "")
            title = str(summary) if summary else "(kein Titel)"

            # Google may return cancellation tombstones with only id/status.
            # Normalize cancellation before requiring event timestamps.
            is_cancelled = item.get("status") == "cancelled"
            start_info = item.get("start", {})
            end_info = item.get("end", {})

            # Handle dateTime or date (all-day events)
            start_str = start_info.get("dateTime") or start_info.get("date")
            end_str = end_info.get("dateTime") or end_info.get("date")

            if start_str is None or end_str is None:
                if not is_cancelled:
                    continue
                start_at = datetime.min.replace(tzinfo=UTC)
                end_at = start_at
            else:
                try:
                    # Date-only events start/end at midnight UTC.
                    if "T" in start_str:
                        start_at = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    else:
                        start_at = datetime.fromisoformat(start_str).replace(tzinfo=UTC)
                    if "T" in end_str:
                        end_at = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    else:
                        end_at = datetime.fromisoformat(end_str).replace(tzinfo=UTC)
                except ValueError:
                    continue

            description = item.get("description")
            if description is not None:
                description = str(description).strip()

            # Cancellation tombstones must survive client-side time filtering;
            # their timestamps may be absent and are not part of their identity.
            if not is_cancelled:
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
                    is_cancelled=is_cancelled,
                    revision_marker=item.get("etag"),
                    resource_id=uid,
                )
            )

        return events

    async def update_event_times(
        self, credentials: dict, event: RawCalendarEvent, *, start_at: datetime, end_at: datetime
    ) -> str | None:
        access_token = credentials.get("access_token")
        if not access_token:
            raise CalendarConnectorError("Google access_token fehlt")
        headers = {"Authorization": f"Bearer {access_token}"}
        if event.revision_marker:
            headers["If-Match"] = event.revision_marker
        try:
            response = await self._client.patch(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{quote(event.uid, safe='')}",
                headers=headers,
                json={"start": {"dateTime": start_at.isoformat()}, "end": {"dateTime": end_at.isoformat()}},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CalendarConnectorError("Google Kalender-Aktualisierung fehlgeschlagen") from exc
        return response.json().get("etag")

    async def delete_event(self, credentials: dict, event: RawCalendarEvent) -> None:
        access_token = credentials.get("access_token")
        if not access_token:
            raise CalendarConnectorError("Google access_token fehlt")
        headers = {"Authorization": f"Bearer {access_token}"}
        if event.revision_marker:
            headers["If-Match"] = event.revision_marker
        await delete_resource(
            self._client,
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{quote(event.uid, safe='')}",
            headers=headers,
        )
