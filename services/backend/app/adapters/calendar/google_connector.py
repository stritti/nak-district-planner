"""Google Calendar connector.

Fetches events from Google Calendar API and converts them into
RawCalendarEvent value objects suitable for the sync service.

Credentials format: {"access_token": "ya29.a0AfH6SMB..."}
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import httpx

from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector


def _content_hash(uid: str, start_at: datetime, end_at: datetime, title: str) -> str:
    payload = f"{uid}|{start_at.isoformat()}|{end_at.isoformat()}|{title}"
    return hashlib.sha256(payload.encode()).hexdigest()


class GoogleCalendarConnector(CalendarConnector):
    """Adapter for Google Calendar API."""

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
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

        params: dict[str, Any] = {
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if from_dt is not None:
            params["timeMin"] = from_dt.isoformat()
        if to_dt is not None:
            params["timeMax"] = to_dt.isoformat()

        headers = {"Authorization": f"Bearer {access_token}"}

        response = await self._client.get(url, params=params, headers=headers)
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            raise ValueError(
                f"URL liefert HTML statt eines Kalenders (Content-Type: {content_type}). "
                "Bitte die direkte .ics-URL verwenden."
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"HTTP {exc.response.status_code} beim Laden des Google Kalenders: {exc}"
            ) from exc

        data = response.json()
        items = data.get("items", [])

        events: list[RawCalendarEvent] = []
        for item in items:
            uid = item.get("id", "")
            if not uid:
                continue

            summary = item.get("summary", "")
            title = str(summary) if summary else "(kein Titel)"

            start_info = item.get("start", {})
            end_info = item.get("end", {})

            # Handle dateTime or date (all-day events)
            start_str = start_info.get("dateTime") or start_info.get("date")
            end_str = end_info.get("dateTime") or end_info.get("date")

            if start_str is None or end_str is None:
                continue

            try:
                # If it's a date (all-day), treat as starting at midnight of that day
                if "T" in start_str:
                    start_at = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                else:
                    start_at = datetime.fromisoformat(start_str).replace(tzinfo=UTC)

                if "T" in end_str:
                    end_at = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                else:
                    # All-day events: end is exclusive (the day after the last full day)
                    # So if end date is 2026-04-06, the event ends at 2026-04-06 00:00:00 UTC
                    end_at = datetime.fromisoformat(end_str).replace(tzinfo=UTC)
            except ValueError:
                # If parsing fails, skip this event
                continue

            description = item.get("description")
            if description is not None:
                description = str(description).strip()

            # Google Calendar uses status field; cancelled events have status="cancelled"
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
