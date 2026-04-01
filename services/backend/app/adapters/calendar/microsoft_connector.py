"""Microsoft Graph Calendar connector.

Fetches events from Microsoft Graph API and converts them into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"access_token": "EwBgA8l6BAAUE..."}
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

import httpx

from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector


def _content_hash(uid: str, start_at: datetime, end_at: datetime, title: str) -> str:
    payload = f"{uid}|{start_at.isoformat()}|{end_at.isoformat()}|{title}"
    return hashlib.sha256(payload.encode()).hexdigest()


class MicrosoftGraphCalendarConnector(CalendarConnector):
    """Adapter for Microsoft Graph Calendar API."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        access_token: str = credentials["access_token"]
        # Use primary calendar; could be made configurable
        url = "https://graph.microsoft.com/v1.0/me/calendar/calendarView"

        params: dict[str, Any] = {}
        if from_dt is not None:
            params["startDateTime"] = from_dt.isoformat()
        if to_dt is not None:
            params["endDateTime"] = to_dt.isoformat()
        else:
            # If no to_dt, fetch a reasonable default (e.g., next 30 days)
            # But we rely on the caller to provide meaningful bounds
            pass
        params["$select"] = "subject,start,end,bodyPreview,iCalUId,status"

        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self._client.get(url, params=params, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"HTTP {exc.response.status_code} beim Laden des Microsoft Kalenders: {exc}"
            ) from exc

        data = response.json()
        items = data.get("value", [])

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
            except ValueError:
                # If parsing fails, skip this event
                continue

            description = item.get("bodyPreview")
            if description is not None:
                description = str(description).strip()

            # Microsoft Graph uses status field; cancelled events have status="cancelled"
            status = item.get("status")
            is_cancelled = status == "cancelled"

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
