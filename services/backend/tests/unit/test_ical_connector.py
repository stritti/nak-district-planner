"""Unit tests for ICalConnector.

All HTTP calls are intercepted via a mock httpx.AsyncClient — no network needed.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapters.calendar.ical_connector import ICalConnector, _content_hash, _to_utc

# ── ICS helpers ───────────────────────────────────────────────────────────────

CREDS = {"url": "https://example.com/calendar.ics"}


def _ics(*vevents: str) -> bytes:
    """Wrap VEVENT strings in a minimal VCALENDAR envelope."""
    body = "\r\n".join(vevents)
    return (
        f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//UnitTest//EN\r\n{body}\r\nEND:VCALENDAR\r\n"
    ).encode()


def _mock_http(
    content: bytes = b"",
    content_type: str = "text/calendar",
    raise_error: Exception | None = None,
) -> AsyncMock:
    """Return a mock httpx.AsyncClient whose get() returns a fake response."""
    response = MagicMock()
    response.content = content
    response.headers = {"content-type": content_type}
    if raise_error:
        response.raise_for_status = MagicMock(side_effect=raise_error)
    else:
        response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    return client


def _http_error(status: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        message=f"{status}",
        request=httpx.Request("GET", "https://example.com"),
        response=httpx.Response(status),
    )


# ── sample VEVENT blocks ──────────────────────────────────────────────────────

VEVENT_BASIC = (
    "BEGIN:VEVENT\r\n"
    "UID:uid-basic@test\r\n"
    "SUMMARY:Gottesdienst\r\n"
    "DTSTART:20260301T100000Z\r\n"
    "DTEND:20260301T120000Z\r\n"
    "DESCRIPTION:Sonntagsgottesdienst\r\n"
    "END:VEVENT"
)

VEVENT_CANCELLED = (
    "BEGIN:VEVENT\r\n"
    "UID:uid-cancelled@test\r\n"
    "SUMMARY:Abgesagt\r\n"
    "DTSTART:20260305T100000Z\r\n"
    "DTEND:20260305T120000Z\r\n"
    "STATUS:CANCELLED\r\n"
    "END:VEVENT"
)

VEVENT_ALLDAY = (
    "BEGIN:VEVENT\r\n"
    "UID:uid-allday@test\r\n"
    "SUMMARY:Feiertag\r\n"
    "DTSTART;VALUE=DATE:20260315\r\n"
    "DTEND;VALUE=DATE:20260316\r\n"
    "END:VEVENT"
)

VEVENT_NO_UID = (
    "BEGIN:VEVENT\r\n"
    "SUMMARY:Ohne UID\r\n"
    "DTSTART:20260310T090000Z\r\n"
    "DTEND:20260310T110000Z\r\n"
    "END:VEVENT"
)

VEVENT_DURATION = (
    "BEGIN:VEVENT\r\n"
    "UID:uid-duration@test\r\n"
    "SUMMARY:Mit Dauer\r\n"
    "DTSTART:20260320T140000Z\r\n"
    "DURATION:PT2H\r\n"
    "END:VEVENT"
)

VEVENT_NO_DTEND = (
    "BEGIN:VEVENT\r\n"
    "UID:uid-nodtend@test\r\n"
    "SUMMARY:Ohne Ende\r\n"
    "DTSTART:20260325T100000Z\r\n"
    "END:VEVENT"
)

# ── _to_utc ───────────────────────────────────────────────────────────────────


class TestToUtc:
    def test_aware_datetime_converted_to_utc(self):
        cet = timezone(timedelta(hours=1))
        aware = datetime(2026, 3, 1, 11, 0, tzinfo=cet)
        assert _to_utc(aware) == datetime(2026, 3, 1, 10, 0, tzinfo=UTC)

    def test_naive_datetime_treated_as_utc(self):
        naive = datetime(2026, 3, 1, 10, 0)
        assert _to_utc(naive) == datetime(2026, 3, 1, 10, 0, tzinfo=UTC)

    def test_date_becomes_midnight_utc(self):
        assert _to_utc(date(2026, 3, 15)) == datetime(2026, 3, 15, 0, 0, tzinfo=UTC)


# ── _content_hash ─────────────────────────────────────────────────────────────


class TestContentHash:
    def test_deterministic(self):
        dt = datetime(2026, 3, 1, 10, tzinfo=UTC)
        h1 = _content_hash("uid", dt, dt, "title")
        h2 = _content_hash("uid", dt, dt, "title")
        assert h1 == h2

    def test_changes_on_title_change(self):
        dt = datetime(2026, 3, 1, 10, tzinfo=UTC)
        assert _content_hash("uid", dt, dt, "A") != _content_hash("uid", dt, dt, "B")

    def test_changes_on_time_change(self):
        dt1 = datetime(2026, 3, 1, 10, tzinfo=UTC)
        dt2 = datetime(2026, 3, 1, 11, tzinfo=UTC)
        assert _content_hash("uid", dt1, dt1, "T") != _content_hash("uid", dt2, dt2, "T")

    def test_changes_on_uid_change(self):
        dt = datetime(2026, 3, 1, 10, tzinfo=UTC)
        assert _content_hash("uid-A", dt, dt, "T") != _content_hash("uid-B", dt, dt, "T")


# ── ICalConnector.fetch_events ────────────────────────────────────────────────


class TestFetchEvents:
    async def test_valid_ics_returns_event(self):
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_BASIC)))
        events = await connector.fetch_events(CREDS)
        assert len(events) == 1
        ev = events[0]
        assert ev.uid == "uid-basic@test"
        assert ev.title == "Gottesdienst"
        assert ev.start_at == datetime(2026, 3, 1, 10, tzinfo=UTC)
        assert ev.end_at == datetime(2026, 3, 1, 12, tzinfo=UTC)
        assert ev.description == "Sonntagsgottesdienst"
        assert ev.is_cancelled is False

    async def test_cancelled_status_sets_flag(self):
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_CANCELLED)))
        events = await connector.fetch_events(CREDS)
        assert len(events) == 1
        assert events[0].is_cancelled is True

    async def test_all_day_event_becomes_midnight_utc(self):
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_ALLDAY)))
        events = await connector.fetch_events(CREDS)
        assert len(events) == 1
        assert events[0].start_at == datetime(2026, 3, 15, 0, 0, tzinfo=UTC)

    async def test_event_without_uid_is_skipped(self):
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_NO_UID)))
        assert await connector.fetch_events(CREDS) == []

    async def test_duration_used_when_dtend_absent(self):
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_DURATION)))
        events = await connector.fetch_events(CREDS)
        assert len(events) == 1
        assert events[0].end_at == datetime(2026, 3, 20, 16, tzinfo=UTC)  # 14:00 + 2h

    async def test_allday_fallback_when_no_dtend_or_duration(self):
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_NO_DTEND)))
        events = await connector.fetch_events(CREDS)
        assert len(events) == 1
        # default: start + 1 day
        assert events[0].end_at == events[0].start_at + timedelta(days=1)

    async def test_content_hash_is_populated(self):
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_BASIC)))
        events = await connector.fetch_events(CREDS)
        assert len(events[0].content_hash) == 64  # SHA-256 hex

    async def test_multiple_events_returned(self):
        connector = ICalConnector(
            client=_mock_http(_ics(VEVENT_BASIC, VEVENT_CANCELLED, VEVENT_ALLDAY))
        )
        events = await connector.fetch_events(CREDS)
        assert len(events) == 3

    async def test_from_dt_filter_excludes_ended_events(self):
        # VEVENT_BASIC ends 2026-03-01 12:00Z — cutoff is 2026-03-02 → excluded
        cutoff = datetime(2026, 3, 2, tzinfo=UTC)
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_BASIC, VEVENT_CANCELLED)))
        events = await connector.fetch_events(CREDS, from_dt=cutoff)
        assert len(events) == 1
        assert events[0].uid == "uid-cancelled@test"

    async def test_to_dt_filter_excludes_future_events(self):
        # VEVENT_CANCELLED starts 2026-03-05 — cutoff is 2026-03-04 → excluded
        to = datetime(2026, 3, 4, tzinfo=UTC)
        connector = ICalConnector(client=_mock_http(_ics(VEVENT_BASIC, VEVENT_CANCELLED)))
        events = await connector.fetch_events(CREDS, to_dt=to)
        assert len(events) == 1
        assert events[0].uid == "uid-basic@test"

    async def test_http_404_raises_value_error(self):
        connector = ICalConnector(client=_mock_http(b"", raise_error=_http_error(404)))
        with pytest.raises(ValueError, match="404"):
            await connector.fetch_events(CREDS)

    async def test_http_401_raises_value_error(self):
        connector = ICalConnector(client=_mock_http(b"", raise_error=_http_error(401)))
        with pytest.raises(ValueError, match="401"):
            await connector.fetch_events(CREDS)

    async def test_http_500_raises_value_error(self):
        connector = ICalConnector(client=_mock_http(b"", raise_error=_http_error(500)))
        with pytest.raises(ValueError, match="500"):
            await connector.fetch_events(CREDS)

    async def test_html_response_raises_value_error(self):
        connector = ICalConnector(
            client=_mock_http(b"<html>login</html>", content_type="text/html; charset=utf-8")
        )
        with pytest.raises(ValueError, match="HTML"):
            await connector.fetch_events(CREDS)
