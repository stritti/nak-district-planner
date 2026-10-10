# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Unit tests for CalDAVConnector.

Since CalDAV involves complex XML parsing and HTTP REPORT requests,
we'll focus on testing the basic structure and error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from icalendar import Calendar as ICalendar

from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.ical_events import content_hash as _content_hash
from app.adapters.calendar.ical_events import to_utc as _to_utc
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnectorError

CREDS = {
    "url": "https://example.com/calendars/user/default/",
    "username": "user",
    "password": "pass",
}


def test_content_hash_deterministic() -> None:
    h1 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title",
    )
    h2 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title",
    )
    assert h1 == h2


def test_content_hash_changes_on_title_change() -> None:
    h1 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title A",
    )
    h2 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title B",
    )
    assert h1 != h2


def test_content_hash_changes_on_time_change() -> None:
    h1 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title",
    )
    h2 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 14, tzinfo=UTC),
        "Title",
    )
    assert h1 != h2


class TestCalDAVConnectorBasics:
    def test_init_with_client(self) -> None:
        """Test that we can inject a custom httpx client."""
        mock_client = MagicMock()
        connector = CalDAVConnector(client=mock_client)
        assert connector._client == mock_client

    def test_init_without_client_creates_one(self) -> None:
        """Test that a default client is created when none is provided."""
        connector = CalDAVConnector()
        assert isinstance(connector._client, httpx.AsyncClient)

    def test_format_datetime(self) -> None:
        """Test the datetime formatting helper."""
        connector = CalDAVConnector()

        # Test with timezone-aware datetime
        dt = datetime(2026, 4, 5, 10, 30, 0, tzinfo=UTC)
        formatted = connector._format_datetime(dt)
        assert formatted == "20260405T103000Z"

        # Test with naive datetime (should be treated as UTC)
        dt_naive = datetime(2026, 4, 5, 10, 30, 0)
        formatted_naive = connector._format_datetime(dt_naive)
        assert formatted_naive == "20260405T103000Z"


_CURRENT_RESOURCE = b"""BEGIN:VCALENDAR\r
VERSION:2.0\r
PRODID:-//Provider//Calendar//EN\r
BEGIN:VEVENT\r
UID:uid@test\r
SUMMARY:Remote title\r
DESCRIPTION:Remote description\r
DTSTART:20260410T090000Z\r
DTEND:20260410T100000Z\r
X-REMOTE-ONLY:keep-me\r
END:VEVENT\r
END:VCALENDAR\r
"""


def _raw_event(*, revision_marker: str | None = None) -> RawCalendarEvent:
    return RawCalendarEvent(
        uid="uid@test",
        title="Stale internal title",
        start_at=datetime(2026, 4, 10, 9, tzinfo=UTC),
        end_at=datetime(2026, 4, 10, 10, tzinfo=UTC),
        description="Stale internal description",
        content_hash="hash",
        is_cancelled=False,
        revision_marker=revision_marker,
        resource_id="event.ics",
    )


def _response(method: str, status: int, *, content: bytes = b"", etag: str | None = None):
    headers = {"etag": etag} if etag else None
    return httpx.Response(
        status,
        content=content,
        headers=headers,
        request=httpx.Request(method, "https://example.com/calendars/user/default/event.ics"),
    )


@pytest.mark.asyncio
async def test_update_event_times_preserves_current_remote_fields() -> None:
    client = AsyncMock()
    client.get.return_value = _response(
        "GET", 200, content=_CURRENT_RESOURCE, etag='"current-etag"'
    )
    client.put.return_value = _response("PUT", 204, etag='"new-etag"')
    connector = CalDAVConnector(client=client)
    new_start = datetime(2026, 4, 10, 11, tzinfo=UTC)
    new_end = datetime(2026, 4, 10, 12, tzinfo=UTC)

    revision = await connector.update_event_times(
        CREDS,
        _raw_event(),
        start_at=new_start,
        end_at=new_end,
    )

    assert revision == '"new-etag"'
    put_kwargs = client.put.await_args.kwargs
    assert put_kwargs["headers"]["If-Match"] == '"current-etag"'
    updated = ICalendar.from_ical(put_kwargs["content"])
    component = next(item for item in updated.walk() if item.name == "VEVENT")
    assert str(component["SUMMARY"]) == "Remote title"
    assert str(component["DESCRIPTION"]) == "Remote description"
    assert str(component["X-REMOTE-ONLY"]) == "keep-me"
    assert _to_utc(component["DTSTART"]) == new_start
    assert _to_utc(component["DTEND"]) == new_end


@pytest.mark.asyncio
async def test_update_event_times_keeps_acknowledged_revision_for_normal_write() -> None:
    client = AsyncMock()
    client.get.return_value = _response(
        "GET", 200, content=_CURRENT_RESOURCE, etag='"current-etag"'
    )
    client.put.return_value = _response("PUT", 204, etag='"new-etag"')
    connector = CalDAVConnector(client=client)

    await connector.update_event_times(
        CREDS,
        _raw_event(revision_marker='"acknowledged-etag"'),
        start_at=datetime(2026, 4, 10, 11, tzinfo=UTC),
        end_at=datetime(2026, 4, 10, 12, tzinfo=UTC),
    )

    assert client.put.await_args.kwargs["headers"]["If-Match"] == '"acknowledged-etag"'


@pytest.mark.asyncio
async def test_update_event_times_maps_resource_fetch_failure() -> None:
    client = AsyncMock()
    client.get.return_value = _response("GET", 503)
    connector = CalDAVConnector(client=client)

    with pytest.raises(CalendarConnectorError, match="Ressource konnte nicht geladen"):
        await connector.update_event_times(
            CREDS,
            _raw_event(),
            start_at=datetime(2026, 4, 10, 11, tzinfo=UTC),
            end_at=datetime(2026, 4, 10, 12, tzinfo=UTC),
        )

    client.put.assert_not_awaited()


# Full fetch_events parsing is covered by dedicated adapter/integration tests.
