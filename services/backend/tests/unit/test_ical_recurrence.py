"""Recurrence, timezone and identity handling for ICS/CalDAV feeds (#465).

The fixtures under ``tests/fixtures/ics`` mirror a congregation calendar as
exported by Thunderbird: a weekly service series that started months ago,
crosses the 2026 DST change, has one EXDATE and one moved occurrence
(RECURRENCE-ID), plus floating, all-day, single and far-future events.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.ical_connector import ICalConnector

FIXTURES = Path(__file__).parent.parent / "fixtures" / "ics"
SERIES = "gd-sonntag-0001@gemeinde-mitte.example"
WINDOW = {
    "from_dt": datetime(2026, 3, 1, tzinfo=UTC),
    "to_dt": datetime(2026, 4, 30, tzinfo=UTC),
}


def _client(body: bytes) -> AsyncMock:
    response = MagicMock(content=body, headers={"content-type": "text/calendar"})
    response.raise_for_status = MagicMock()
    return AsyncMock(get=AsyncMock(return_value=response))


async def _fetch(name: str = "gemeinde_mitte.ics", **window):
    connector = ICalConnector(client=_client((FIXTURES / name).read_bytes()))
    return await connector.fetch_events({"url": "https://example.com/cal.ics"}, **(window or WINDOW))


def _by_uid(events):
    return {event.uid: event for event in events}


async def test_weekly_series_is_expanded_across_dst_with_exdate_and_override():
    events = _by_uid(await _fetch())

    sundays = sorted(
        (uid for uid in events if uid.startswith(SERIES)), key=lambda uid: events[uid].start_at
    )
    assert [events[uid].start_at for uid in sundays] == [
        datetime(2026, 3, 1, 9, tzinfo=UTC),  # CET: 10:00 local
        datetime(2026, 3, 8, 9, tzinfo=UTC),
        datetime(2026, 3, 15, 9, tzinfo=UTC),
        # 2026-03-22 removed by EXDATE
        datetime(2026, 3, 29, 8, tzinfo=UTC),  # CEST from 2026-03-29
        datetime(2026, 4, 5, 7, 30, tzinfo=UTC),  # RECURRENCE-ID override, moved to 09:30
        datetime(2026, 4, 12, 8, tzinfo=UTC),
        datetime(2026, 4, 19, 8, tzinfo=UTC),
        datetime(2026, 4, 26, 8, tzinfo=UTC),
    ]
    override = events[f"{SERIES}::20260405T080000Z"]
    assert override.title == "Ostergottesdienst"
    assert override.end_at == datetime(2026, 4, 5, 9, tzinfo=UTC)
    assert events[f"{SERIES}::20260329T080000Z"].end_at == datetime(2026, 3, 29, 9, 30, tzinfo=UTC)


async def test_series_master_older_than_window_still_yields_occurrences():
    """The master DTSTART (2025-11-02) lies far before the window start."""
    events = await _fetch(from_dt=datetime(2026, 4, 20, tzinfo=UTC), to_dt=datetime(2026, 4, 30, tzinfo=UTC))
    in_window = [event.uid for event in events if not event.outside_window]
    assert in_window == [f"{SERIES}::20260426T080000Z"]


async def test_non_recurring_events_keep_plain_uid():
    events = _by_uid(await _fetch())
    assert "aemterstunde-2026-04-10@gemeinde-mitte.example" in events
    assert SERIES not in events


async def test_floating_and_all_day_times_use_district_timezone():
    events = _by_uid(await _fetch())

    floating = events["chorprobe-2026-04-01@gemeinde-mitte.example"]
    assert floating.start_at == datetime(2026, 4, 1, 17, 30, tzinfo=UTC)
    assert floating.end_at == datetime(2026, 4, 1, 19, tzinfo=UTC)

    all_day = events["bezirksjugendtag-2026@gemeinde-mitte.example"]
    assert all_day.start_at == datetime(2026, 4, 17, 22, tzinfo=UTC)
    assert all_day.end_at == datetime(2026, 4, 18, 22, tzinfo=UTC)


async def test_repeated_fetch_is_stable():
    first, second = await _fetch(), await _fetch()
    assert [(e.uid, e.content_hash) for e in first] == [(e.uid, e.content_hash) for e in second]
    assert len({e.uid for e in first}) == len(first)


def test_ics_feed_is_an_authoritative_snapshot():
    assert ICalConnector.authoritative_snapshot is True


# ── CalDAV ────────────────────────────────────────────────────────────────────


def _multistatus(calendar_data: str) -> bytes:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:href>/calendars/gemeinde/gd-sonntag.ics</D:href>
    <D:propstat><D:prop>
      <D:getetag>"etag-1"</D:getetag>
      <C:calendar-data>{calendar_data}</C:calendar-data>
    </D:prop><D:status>HTTP/1.1 200 OK</D:status></D:propstat>
  </D:response>
</D:multistatus>""".encode()


def _caldav(body: bytes) -> tuple[CalDAVConnector, AsyncMock]:
    response = MagicMock(content=body)
    response.raise_for_status = MagicMock()
    client = AsyncMock(request=AsyncMock(return_value=response))
    return CalDAVConnector(client=client), client


CALDAV_CREDS = {"url": "https://dav.example.com/calendars/gemeinde/", "username": "u", "password": "p"}


async def test_caldav_expands_recurring_resource_with_occurrence_identity():
    connector, _ = _caldav(_multistatus((FIXTURES / "gemeinde_mitte.ics").read_text()))
    events = _by_uid(await connector.fetch_events(CALDAV_CREDS, **WINDOW))
    occurrence = events[f"{SERIES}::20260329T080000Z"]
    assert occurrence.start_at == datetime(2026, 3, 29, 8, tzinfo=UTC)
    assert occurrence.resource_id == "/calendars/gemeinde/gd-sonntag.ics"
    assert occurrence.revision_marker == '"etag-1"'
    assert f"{SERIES}::20260322T090000Z" not in events


async def test_caldav_query_has_bounded_time_range():
    connector, client = _caldav(_multistatus(""))
    await connector.fetch_events(CALDAV_CREDS, **WINDOW)
    body = client.request.await_args.kwargs["data"].decode()
    assert 'start="20260301T000000Z"' in body
    assert 'end="20260430T000000Z"' in body


@pytest.mark.parametrize(
    ("window", "present", "absent"),
    [
        ({"from_dt": datetime(2026, 3, 1, tzinfo=UTC)}, 'start="20260301T000000Z"', "end="),
        ({"to_dt": datetime(2026, 4, 30, tzinfo=UTC)}, 'end="20260430T000000Z"', "start="),
        ({}, "VEVENT", "time-range"),
    ],
)
async def test_caldav_query_omits_unset_time_range_attributes(window, present, absent):
    connector, client = _caldav(_multistatus(""))
    await connector.fetch_events(CALDAV_CREDS, **window)
    body = client.request.await_args.kwargs["data"].decode()
    assert present in body
    assert absent not in body
    assert '=""' not in body


async def test_caldav_refuses_writes_to_a_single_occurrence():
    """Writing back one occurrence would rewrite or delete the whole series resource."""
    from app.domain.models.raw_calendar_event import RawCalendarEvent
    from app.domain.ports.calendar import CalendarConnectorError

    connector, client = _caldav(b"")
    occurrence = RawCalendarEvent(
        uid=f"{SERIES}::20260329T080000Z", title="Gottesdienst",
        start_at=datetime(2026, 3, 29, 8, tzinfo=UTC), end_at=datetime(2026, 3, 29, 9, 30, tzinfo=UTC),
        description=None, content_hash="", is_cancelled=False,
        resource_id="/calendars/gemeinde/gd-sonntag.ics",
        series_uid=SERIES, recurrence_id="20260329T080000Z",
    )
    with pytest.raises(CalendarConnectorError):
        await connector.delete_event(CALDAV_CREDS, occurrence)
    with pytest.raises(CalendarConnectorError):
        await connector.update_event_times(
            CALDAV_CREDS, occurrence, start_at=occurrence.start_at, end_at=occurrence.end_at
        )
    client.delete.assert_not_called()
    client.put.assert_not_called()


async def test_caldav_identity_is_not_parsed_from_the_uid():
    """A plain UID that happens to contain '::' is an ordinary single event."""
    from app.domain.models.raw_calendar_event import RawCalendarEvent

    connector, client = _caldav(b"")
    client.delete = AsyncMock(return_value=MagicMock(status_code=204, raise_for_status=MagicMock()))
    single = RawCalendarEvent(
        uid="urn::legacy::event-7", title="Einzeltermin",
        start_at=datetime(2026, 3, 29, 8, tzinfo=UTC), end_at=datetime(2026, 3, 29, 9, tzinfo=UTC),
        description=None, content_hash="", is_cancelled=False,
        resource_id="/calendars/gemeinde/event-7.ics",
    )
    await connector.delete_event(CALDAV_CREDS, single)
    client.delete.assert_awaited_once()


# ── Codex review of PR #483 ──────────────────────────────────────────────────


def _feed(*vevents: str) -> bytes:
    body = "\r\n".join(vevents)
    return f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//T//EN\r\n{body}\r\nEND:VCALENDAR\r\n".encode()


def _series(uid: str, dtstart: str, rrule: str) -> str:
    return (
        f"BEGIN:VEVENT\r\nUID:{uid}\r\nSUMMARY:Serie\r\nDTSTART:{dtstart}\r\n"
        f"DURATION:PT1H\r\nRRULE:{rrule}\r\nEND:VEVENT"
    )


async def _fetch_body(body: bytes, **window):
    connector = ICalConnector(client=_client(body))
    return await connector.fetch_events({"url": "https://example.com/cal.ics"}, **(window or WINDOW))


async def test_occurrences_carry_explicit_series_identity():
    events = _by_uid(await _fetch())
    occurrence = events[f"{SERIES}::20260329T080000Z"]
    assert (occurrence.series_uid, occurrence.recurrence_id) == (SERIES, "20260329T080000Z")
    single = events["aemterstunde-2026-04-10@gemeinde-mitte.example"]
    assert (single.series_uid, single.recurrence_id) == (None, None)


async def test_long_series_uid_keeps_storage_key_within_column_limit():
    uid = "x" * 490 + "@example"
    events = await _fetch_body(_feed(_series(uid, "20260301T090000Z", "FREQ=WEEKLY;COUNT=2")))
    again = await _fetch_body(_feed(_series(uid, "20260301T090000Z", "FREQ=WEEKLY;COUNT=2")))
    assert len(events) == 2
    assert all(len(event.uid) <= 500 for event in events)
    assert len({event.uid for event in events}) == 2
    assert [e.uid for e in events] == [e.uid for e in again]
    assert events[0].series_uid == uid


@pytest.mark.parametrize(
    "rrule", ["FREQ=SECONDLY", "FREQ=MINUTELY", "FREQ=DAILY;BYHOUR=0,1,2,3,4,5,6,7,8,9,10,11;BYMINUTE=0,5,10,15,20,25,30,35,40,45,50,55"]
)
async def test_explosive_recurrence_fails_fast(rrule):
    import time

    from app.domain.ports.calendar import CalendarConnectorError

    started = time.monotonic()
    with pytest.raises(CalendarConnectorError):
        await _fetch_body(_feed(_series("dos@example", "20200101T000000Z", rrule)))
    assert time.monotonic() - started < 5


async def test_ancient_daily_series_fails_fast_instead_of_iterating_for_minutes():
    import time

    from app.domain.ports.calendar import CalendarConnectorError

    started = time.monotonic()
    with pytest.raises(CalendarConnectorError):
        await _fetch_body(_feed(_series("old@example", "00010101T000000Z", "FREQ=DAILY")))
    assert time.monotonic() - started < 5


async def test_occurrence_cap_applies_per_feed(monkeypatch):
    from app.config import settings
    from app.domain.ports.calendar import CalendarConnectorError

    monkeypatch.setattr(settings, "sync_max_occurrences", 50)
    with pytest.raises(CalendarConnectorError):
        await _fetch_body(_feed(_series("daily@example", "20260301T090000Z", "FREQ=DAILY")))
    monkeypatch.setattr(settings, "sync_max_occurrences", 5000)
    assert len(await _fetch_body(_feed(_series("daily@example", "20260301T090000Z", "FREQ=DAILY")))) == 60


async def test_events_outside_window_are_reported_as_presence_only():
    """A moved event outside the window still exists and must not be reconciled away."""
    events = _by_uid(await _fetch())
    far = events["jahresfest-2028@gemeinde-mitte.example"]
    assert far.outside_window is True
    assert far.start_at == datetime(2028, 6, 4, 8, tzinfo=UTC)
    assert not any(e.outside_window for uid, e in events.items() if uid != far.uid)
