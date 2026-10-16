# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Microsoft Graph Calendar connector.

Fetches events from Microsoft Graph API and converts them into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"access_token": "EwBgA8l6BAAUE..."}
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from app.adapters.calendar.bounded_http import make_bounded_client
from app.adapters.calendar.deletion import delete_resource
from app.adapters.calendar.http_policy import resilient_request
from app.adapters.calendar.pagination_budget import PaginationBudget
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError


def _validate_next_link(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "graph.microsoft.com":
        raise CalendarConnectorError("Ungültiger Microsoft Graph nextLink")
    return url


class MicrosoftGraphCalendarConnector(CalendarConnector):
    """Adapter for Microsoft Graph Calendar API."""

    # Graph omits events moved outside the query window and offers no cheap
    # presence check here, so missing events are never reconciled as deleted.
    authoritative_snapshot = False

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
        next_url: str | None = url
        next_params: dict[str, Any] | None = params
        while next_url:
            response = await resilient_request(
                lambda next_url=next_url, next_params=next_params: self._client.get(
                    next_url, params=next_params, headers=headers
                ),
                provider="Microsoft",
            )
            data = response.json()
            page_items = data.get("value", [])
            raw_next_url = data.get("@odata.nextLink")
            next_url = _validate_next_link(raw_next_url) if raw_next_url else None
            budget.charge(
                items=len(page_items), size_bytes=len(response.content), next_token=next_url
            )
            items.extend(page_items)
            next_params = None
        return items

    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        access_token = credentials.get("access_token")
        if not access_token:
            raise CalendarConnectorError("Microsoft access_token fehlt")
        # Use primary calendar; could be made configurable
        url = "https://graph.microsoft.com/v1.0/me/calendar/calendarView"

        params: dict[str, Any] = {}
        if from_dt is not None:
            params["startDateTime"] = from_dt.isoformat()
        if to_dt is not None:
            params["endDateTime"] = to_dt.isoformat()
        params["$select"] = "id,subject,start,end,bodyPreview,iCalUId,isCancelled,changeKey"

        headers = {"Authorization": f"Bearer {access_token}"}

        budget = self._budget_factory()
        items = await budget.run(self._fetch_pages(url, params, headers, budget))

        events: list[RawCalendarEvent] = []
        for item in items:
            uid = item.get("iCalUId", "")
            if not uid:
                continue

            subject = item.get("subject", "")
            title = str(subject) if subject else "(kein Titel)"

            start_info = item.get("start", {})
            end_info = item.get("end", {})

            start_str = start_info.get("dateTime")
            end_str = end_info.get("dateTime")

            if start_str is None or end_str is None:
                continue

            try:
                start_at = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_at = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if start_at.tzinfo is None:
                    start_at = start_at.replace(tzinfo=UTC)
                if end_at.tzinfo is None:
                    end_at = end_at.replace(tzinfo=UTC)
            except ValueError:
                # If parsing fails, skip this event
                continue

            description = item.get("bodyPreview")
            if description is not None:
                description = str(description).strip()

            is_cancelled = bool(item.get("isCancelled", False))

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
                    is_cancelled=is_cancelled,
                    revision_marker=item.get("changeKey"),
                    resource_id=item.get("id"),
                )
            )

        return events

    async def update_event_times(
        self, credentials: dict, event: RawCalendarEvent, *, start_at: datetime, end_at: datetime
    ) -> str | None:
        access_token = credentials.get("access_token")
        if not access_token:
            raise CalendarConnectorError("Microsoft access_token fehlt")
        if not event.resource_id:
            raise CalendarConnectorError("Microsoft resource ID fehlt")
        headers = {"Authorization": f"Bearer {access_token}"}
        if event.revision_marker:
            headers["If-Match"] = event.revision_marker
        payload = {
            "start": {"dateTime": start_at.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_at.isoformat(), "timeZone": "UTC"},
        }
        try:
            response = await self._client.patch(
                f"https://graph.microsoft.com/v1.0/me/events/{quote(event.resource_id, safe='')}",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CalendarConnectorError("Microsoft Kalender-Aktualisierung fehlgeschlagen") from exc
        return response.json().get("changeKey")

    async def delete_event(self, credentials: dict, event: RawCalendarEvent) -> None:
        access_token = credentials.get("access_token")
        if not access_token:
            raise CalendarConnectorError("Microsoft access_token fehlt")
        if not event.resource_id:
            raise CalendarConnectorError("Microsoft resource ID fehlt")
        headers = {"Authorization": f"Bearer {access_token}"}
        if event.revision_marker:
            headers["If-Match"] = event.revision_marker
        await delete_resource(
            self._client,
            f"https://graph.microsoft.com/v1.0/me/events/{quote(event.resource_id, safe='')}",
            headers=headers,
        )
