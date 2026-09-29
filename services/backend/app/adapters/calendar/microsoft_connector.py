"""Microsoft Graph Calendar connector.

Fetches events from Microsoft Graph API and converts them into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"access_token": "EwBgA8l6BAAUE..."}
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.adapters.calendar.deletion import delete_resource
from app.adapters.calendar.http_policy import resilient_request
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError


def _content_hash(uid: str, start_at: datetime, end_at: datetime, title: str) -> str:
    payload = f"{uid}|{start_at.isoformat()}|{end_at.isoformat()}|{title}"
    return hashlib.sha256(payload.encode()).hexdigest()


class MicrosoftGraphCalendarConnector(CalendarConnector):
    """Adapter for Microsoft Graph Calendar API."""

    authoritative_snapshot = True

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0)

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
            items.extend(data.get("value", []))
            next_url = data.get("@odata.nextLink")
            next_params = None

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

            # Microsoft Graph uses status field; cancelled events have status="cancelled"
            status = item.get("status")
            is_cancelled = item.get("isCancelled", False) or status == "cancelled"

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
                    revision_marker=item.get("changeKey"),
                    resource_id=item.get("id"),
                )
            )

        return events

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
