"""Unit tests for CalDAVConnector.

All HTTP calls are mocked — no network needed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone, timedelta, date
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapters.calendar.caldav_connector import CalDAVConnector, _content_hash


CREDS_BASIC = {"url": "https://caldav.example.com/cal/", "username": "user", "password": "pass"}
CREDS_BEARER = {"url": "https://caldav.example.com/cal/", "access_token": "tok"}
CREDS_INVALID = {"url": "https://caldav.example.com/cal/"}


def _mock_xml_response(body: str, status: int = 200) -> AsyncMock:
    """Return a mock httpx.AsyncClient that responds with a multi-status XML body."""
    response = MagicMock()
    response.content = body.encode("utf-8")
    response.status_code = status
    if status >= 400:
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                message=f"{status}",
                request=httpx.Request("REPORT", "https://caldav.example.com"),
                response=httpx.Response(status),
            )
        )
    else:
        response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.request = AsyncMock(return_value=response)
    return client


# ── _content_hash ──────────────────────────────────────────────────────────────

class TestContentHash:
    def test_deterministic(self):
        dt = datetime(2026, 3, 1, 10, tzinfo=UTC)
        h1 = _content_hash("uid", dt, dt, "title")
        h2 = _content_hash("uid", dt, dt, "title")
        assert h1 == h2

    def test_changes_on_uid(self):
        dt = datetime(2026, 3, 1, 10, tzinfo=UTC)
        assert _content_hash("a", dt, dt, "T") != _content_hash("b", dt, dt, "T")

    def test_changes_on_start(self):
        dt1 = datetime(2026, 3, 1, 10, tzinfo=UTC)
        dt2 = datetime(2026, 3, 1, 11, tzinfo=UTC)
        assert _content_hash("u", dt1, dt1, "T") != _content_hash("u", dt2, dt2, "T")

    def test_changes_on_title(self):
        dt = datetime(2026, 3, 1, 10, tzinfo=UTC)
        assert _content_hash("u", dt, dt, "A") != _content_hash("u", dt, dt, "B")


# ── CalDAV XML samples ────────────────────────────────────────────────────────

MULTISTATUS_WITH_EVENTS = """<?xml version="1.0" encoding="UTF-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/cal/event-1.ics</D:href>
    <D:propstat>
      <D:prop>
        <D:getetag>"abc123"</D:getetag>
        <C:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:uid-1@test
SUMMARY:Gottesdienst
DTSTART:20260301T100000Z
DTEND:20260301T120000Z
DESCRIPTION:Sonntagsgottesdienst
END:VEVENT
END:VCALENDAR</C:calendar-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

MULTISTATUS_CANCELLED = """<?xml version="1.0" encoding="UTF-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/cal/event-2.ics</D:href>
    <D:propstat>
      <D:prop>
        <C:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:uid-2@test
SUMMARY:Abgesagt
DTSTART:20260305T100000Z
DTEND:20260305T120000Z
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR</C:calendar-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

MULTISTATUS_ALLDAY = """<?xml version="1.0" encoding="UTF-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/cal/event-3.ics</D:href>
    <D:propstat>
      <D:prop>
        <C:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:uid-3@test
SUMMARY:Feiertag
DTSTART;VALUE=DATE:20260315
DTEND;VALUE=DATE:20260316
END:VEVENT
END:VCALENDAR</C:calendar-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

MULTISTATUS_NO_UID = """<?xml version="1.0" encoding="UTF-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/cal/event-4.ics</D:href>
    <D:propstat>
      <D:prop>
        <C:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
SUMMARY:Keine UID
DTSTART:20260310T090000Z
DTEND:20260310T110000Z
END:VEVENT
END:VCALENDAR</C:calendar-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

MULTISTATUS_DURATION = """<?xml version="1.0" encoding="UTF-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/cal/event-5.ics</D:href>
    <D:propstat>
      <D:prop>
        <C:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:uid-5@test
SUMMARY:Mit Dauer
DTSTART:20260320T140000Z
DURATION:PT2H
END:VEVENT
END:VCALENDAR</C:calendar-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""

MULTISTATUS_MULTIPLE = """<?xml version="1.0" encoding="UTF-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/cal/e1.ics</D:href>
    <D:propstat>
      <D:prop>
        <C:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:a@test
SUMMARY:Event A
DTSTART:20260401T100000Z
DTEND:20260401T110000Z
END:VEVENT
END:VCALENDAR</C:calendar-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
  <D:response>
    <D:href>/cal/e2.ics</D:href>
    <D:propstat>
      <D:prop>
        <C:calendar-data>BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//EN
BEGIN:VEVENT
UID:b@test
SUMMARY:Event B
DTSTART:20260402T100000Z
DTEND:20260402T110000Z
END:VEVENT
END:VCALENDAR</C:calendar-data>
      </D:prop>
      <D:status>HTTP/1.1 200 OK</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""


# ── Test _format_datetime ─────────────────────────────────────────────────────

class TestFormatDatetime:
    def test_format_utc_datetime(self):
        connector = CalDAVConnector(client=AsyncMock())
        dt = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
        assert connector._format_datetime(dt) == "20260301T100000Z"

    def test_format_with_timezone(self):
        connector = CalDAVConnector(client=AsyncMock())
        cet = timezone(timedelta(hours=1))
        dt = datetime(2026, 3, 1, 11, 0, tzinfo=cet)
        assert connector._format_datetime(dt) == "20260301T100000Z"

    def test_format_naive_datetime(self):
        connector = CalDAVConnector(client=AsyncMock())
        dt = datetime(2026, 3, 1, 10, 0)
        assert connector._format_datetime(dt) == "20260301T100000Z"

    def test_format_none(self):
        connector = CalDAVConnector(client=AsyncMock())
        assert connector._format_datetime(None) == ""


# ── Test fetch_events ─────────────────────────────────────────────────────────

class TestFetchEvents:
    async def test_basic_event_parsed_correctly(self):
        connector = CalDAVConnector(client=_mock_xml_response(MULTISTATUS_WITH_EVENTS))
        events = await connector.fetch_events(CREDS_BASIC)
        assert len(events) == 1
        ev = events[0]
        assert ev.uid == "uid-1@test"
        assert ev.title == "Gottesdienst"
        assert ev.start_at == datetime(2026, 3, 1, 10, tzinfo=UTC)
        assert ev.end_at == datetime(2026, 3, 1, 12, tzinfo=UTC)
        assert ev.description == "Sonntagsgottesdienst"
        assert ev.is_cancelled is False
        assert len(ev.content_hash) == 64

    async def test_bearer_token_auth(self):
        connector = CalDAVConnector(client=_mock_xml_response(MULTISTATUS_WITH_EVENTS))
        events = await connector.fetch_events(CREDS_BEARER)
        assert len(events) == 1

    async def test_missing_auth_raises(self):
        connector = CalDAVConnector(client=_mock_xml_response(MULTISTATUS_WITH_EVENTS))
        with pytest.raises(ValueError, match="access_token"):
            await connector.fetch_events(CREDS_INVALID)

    async def test_cancelled_status(self):
        connector = CalDAVConnector(client=_mock_xml_response(MULTISTATUS_CANCELLED))
        events = await connector.fetch_events(CREDS_BASIC)
        assert len(events) == 1
        assert events[0].is_cancelled is True

    async def test_allday_event(self):
        connector = CalDAVConnector(client=_mock_xml_response(MULTISTATUS_ALLDAY))
        events = await connector.fetch_events(CREDS_BASIC)
        assert len(events) == 1
        assert events[0].start_at == datetime(2026, 3, 15, 0, tzinfo=UTC)

    async def test_event_without_uid_skipped(self):
        connector = CalDAVConnector(client=_mock_xml_response(MULTISTATUS_NO_UID))
        events = await connector.fetch_events(CREDS_BASIC)
        assert len(events) == 0

    async def test_duration_used_when_dtend_absent(self):
        connector = CalDAVConnector(client=_mock_xml_response(MULTISTATUS_DURATION))
        events = await connector.fetch_events(CREDS_BASIC)
        assert len(events) == 1
        # 14:00 + 2h = 16:00 UTC
        assert events[0].end_at == datetime(2026, 3, 20, 16, tzinfo=UTC)

    async def test_multiple_events(self):
        connector = CalDAVConnector(client=_mock_xml_response(MULTISTATUS_MULTIPLE))
        events = await connector.fetch_events(CREDS_BASIC)
        assert len(events) == 2

    async def test_http_404_raises(self):
        connector = CalDAVConnector(client=_mock_xml_response("<error/>", status=404))
        with pytest.raises(ValueError, match="404"):
            await connector.fetch_events(CREDS_BASIC)

    async def test_http_401_raises(self):
        connector = CalDAVConnector(client=_mock_xml_response("<error/>", status=401))
        with pytest.raises(ValueError, match="401"):
            await connector.fetch_events(CREDS_BASIC)

    async def test_http_500_raises(self):
        connector = CalDAVConnector(client=_mock_xml_response("<error/>", status=500))
        with pytest.raises(ValueError, match="500"):
            await connector.fetch_events(CREDS_BASIC)

    async def test_invalid_xml_raises(self):
        connector = CalDAVConnector(client=_mock_xml_response("not xml"))
        with pytest.raises(ValueError, match="XML"):
            await connector.fetch_events(CREDS_BASIC)

    async def test_empty_multistatus_returns_empty(self):
        body = """<?xml version="1.0" encoding="UTF-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"></D:multistatus>"""
        connector = CalDAVConnector(client=_mock_xml_response(body))
        events = await connector.fetch_events(CREDS_BASIC)
        assert events == []

    async def test_missing_calendar_data_skipped(self):
        body = """<?xml version="1.0" encoding="UTF-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/cal/e.ics</D:href>
    <D:propstat>
      <D:prop></D:prop>
      <D:status>HTTP/1.1 404 Not Found</D:status>
    </D:propstat>
  </D:response>
</D:multistatus>"""
        connector = CalDAVConnector(client=_mock_xml_response(body))
        events = await connector.fetch_events(CREDS_BASIC)
        assert events == []

    async def test_default_connector_creates_own_client(self):
        connector = CalDAVConnector()
        assert connector._client is not None
