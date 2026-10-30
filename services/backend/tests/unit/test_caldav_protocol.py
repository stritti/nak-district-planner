# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""CalDAV contract: REPORT construction, multistatus parsing, hrefs, auth, deletion.

The fixtures are plain DAV responses, independent of how the adapter is built,
so they keep describing the contract if the implementation changes.
"""

from __future__ import annotations

import xml.etree.ElementTree as XMLBuilder  # nosec B405 - parses our own query in tests
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.caldav_protocol import (
    build_calendar_query,
    dav_auth,
    parse_multistatus,
    resource_url,
)
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnectorError

COLLECTION = "https://dav.example.com/calendars/gemeinde/"
CREDS = {"url": COLLECTION, "username": "u", "password": "p"}

VEVENT = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//EN
BEGIN:VEVENT
UID:{uid}
DTSTART:20260301T100000Z
DTEND:20260301T120000Z
SUMMARY:Gottesdienst
END:VEVENT
END:VCALENDAR"""


def _response(
    href: str, etag: str | None, data: str | None, status: str = "HTTP/1.1 200 OK"
) -> str:
    props = (f"<D:getetag>{etag}</D:getetag>" if etag else "") + (
        f"<C:calendar-data>{data}</C:calendar-data>" if data is not None else ""
    )
    return (
        f"<D:response><D:href>{href}</D:href><D:propstat><D:prop>{props}</D:prop>"
        f"<D:status>{status}</D:status></D:propstat></D:response>"
    )


def _multistatus(*responses: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
        + "".join(responses)
        + "</D:multistatus>"
    ).encode()


def _http_response(
    status: int, content: bytes = b"", headers: dict | None = None
) -> httpx.Response:
    return httpx.Response(
        status,
        content=content,
        headers=headers,
        request=httpx.Request("GET", COLLECTION),
    )


def _client(*responses: httpx.Response) -> MagicMock:
    client = MagicMock()
    client.request = AsyncMock(side_effect=list(responses))
    client.get = AsyncMock(side_effect=list(responses))
    client.put = AsyncMock(side_effect=list(responses))
    client.delete = AsyncMock(side_effect=list(responses))
    return client


def _event(**overrides) -> RawCalendarEvent:
    values = {
        "uid": "uid-1",
        "title": "Gottesdienst",
        "start_at": datetime(2026, 3, 1, 10, tzinfo=UTC),
        "end_at": datetime(2026, 3, 1, 12, tzinfo=UTC),
        "description": None,
        "is_cancelled": False,
        "revision_marker": '"etag-1"',
        "resource_id": "/calendars/gemeinde/uid-1.ics",
    }
    values.update(overrides)
    return RawCalendarEvent(**values)


# --- query construction ------------------------------------------------------


def test_query_is_well_formed_xml_with_a_utc_window() -> None:
    query = build_calendar_query(
        datetime(2026, 3, 1, 1, tzinfo=timezone(timedelta(hours=1))),
        datetime(2026, 4, 30),
    )
    root = XMLBuilder.fromstring(query)  # noqa: S314 - our own output
    time_range = root.find(".//{urn:ietf:params:xml:ns:caldav}time-range")
    assert root.tag == "{urn:ietf:params:xml:ns:caldav}calendar-query"
    assert time_range is not None
    assert time_range.attrib == {"start": "20260301T000000Z", "end": "20260430T000000Z"}


def test_query_without_window_has_no_time_range() -> None:
    root = XMLBuilder.fromstring(build_calendar_query(None, None))  # noqa: S314
    assert root.find(".//{urn:ietf:params:xml:ns:caldav}time-range") is None


# --- multistatus parsing -----------------------------------------------------


def test_parsing_keeps_href_and_etag_verbatim() -> None:
    [resource] = parse_multistatus(
        _multistatus(_response("/calendars/gemeinde/a.ics", '"etag-7"', "BEGIN:VCALENDAR"))
    )
    assert resource.href == "/calendars/gemeinde/a.ics"
    assert resource.etag == '"etag-7"'
    assert resource.calendar_data == "BEGIN:VCALENDAR"


def test_missing_resource_has_no_calendar_data() -> None:
    [resource] = parse_multistatus(
        _multistatus(
            _response("/calendars/gemeinde/gone.ics", None, None, "HTTP/1.1 404 Not Found")
        )
    )
    assert resource.calendar_data == ""
    assert resource.etag is None


@pytest.mark.parametrize(
    "content",
    [
        b"not xml",
        b"<D:multistatus xmlns:D='DAV:'>",
        # Entity expansion ("billion laughs")
        b'<?xml version="1.0"?><!DOCTYPE m [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]><m>&b;</m>',
        # External entity (XXE)
        b'<?xml version="1.0"?><!DOCTYPE m [<!ENTITY x SYSTEM "file:///etc/passwd">]><m>&x;</m>',
    ],
)
def test_malformed_or_hostile_xml_fails_without_details(content: bytes) -> None:
    with pytest.raises(CalendarConnectorError) as raised:
        parse_multistatus(content)
    assert str(raised.value) == "Ungültige XML-Antwort vom CalDAV Server"


# --- hrefs ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("href", "expected"),
    [
        ("uid-1.ics", "https://dav.example.com/calendars/gemeinde/uid-1.ics"),
        ("/calendars/gemeinde/uid-1.ics", "https://dav.example.com/calendars/gemeinde/uid-1.ics"),
        (
            "https://dav.example.com/calendars/gemeinde/uid-1.ics",
            "https://dav.example.com/calendars/gemeinde/uid-1.ics",
        ),
        (
            "/calendars/gemeinde/Gottesdienst%20Sonntag.ics",
            "https://dav.example.com/calendars/gemeinde/Gottesdienst%20Sonntag.ics",
        ),
    ],
)
def test_hrefs_inside_the_collection_resolve(href: str, expected: str) -> None:
    assert resource_url(COLLECTION, href) == expected


@pytest.mark.parametrize(
    "href",
    [
        "https://evil.example.com/calendars/gemeinde/uid-1.ics",
        "//evil.example.com/calendars/gemeinde/uid-1.ics",
        "http://dav.example.com/calendars/gemeinde/uid-1.ics",
        "/calendars/other/uid-1.ics",
        "/calendars/gemeinde-evil/uid-1.ics",
        "../other/uid-1.ics",
        "https://dav.example.com/calendars/gemeinde/../other/uid-1.ics",
        "/calendars/gemeinde/%2e%2e/other/uid-1.ics",
        "/calendars/gemeinde/%2E%2E%2Fother/uid-1.ics",
        "/calendars/gemeinde/..%5Cother/uid-1.ics",
        "/calendars/gemeinde/uid-1.ics?export",
        "/calendars/gemeinde/uid-1.ics#x",
        "/calendars/gemeinde/",
        "/calendars/gemeinde",
    ],
)
def test_hrefs_escaping_the_collection_are_refused(href: str) -> None:
    with pytest.raises(CalendarConnectorError, match="außerhalb des Kalenders"):
        resource_url(COLLECTION, href)


# --- auth ----------------------------------------------------------------------


def test_bearer_token_wins_and_basic_needs_both_fields() -> None:
    assert dav_auth({"access_token": "t", "username": "u", "password": "p"}).headers == {
        "Authorization": "Bearer t"
    }
    assert dav_auth(CREDS).basic == ("u", "p")
    with pytest.raises(CalendarConnectorError, match="access_token"):
        dav_auth({"username": "u"})


# --- connector behaviour ---------------------------------------------------------


async def test_fetch_keeps_resource_identity_and_marks_missing_resources_incomplete() -> None:
    body = _multistatus(
        _response("/calendars/gemeinde/a.ics", '"e-a"', VEVENT.format(uid="a")),
        _response("/calendars/gemeinde/gone.ics", None, None, "HTTP/1.1 404 Not Found"),
    )
    connector = CalDAVConnector(client=_client(_http_response(207, body)))
    [event] = await connector.fetch_events(CREDS)
    assert (event.uid, event.resource_id, event.revision_marker) == (
        "a",
        "/calendars/gemeinde/a.ics",
        '"e-a"',
    )
    assert connector.snapshot_complete is False


async def test_fetch_retries_a_transient_server_error() -> None:
    body = _multistatus(_response("/calendars/gemeinde/a.ics", '"e"', VEVENT.format(uid="a")))
    client = _client(_http_response(503), _http_response(207, body))
    events = await CalDAVConnector(client=client).fetch_events(CREDS)
    assert [e.uid for e in events] == ["a"]
    assert client.request.await_count == 2


@pytest.mark.parametrize("status", [401, 403, 404])
async def test_fetch_does_not_retry_permanent_failures(status: int) -> None:
    client = _client(_http_response(status))
    with pytest.raises(CalendarConnectorError, match="konnte nicht geladen werden") as raised:
        await CalDAVConnector(client=client).fetch_events(CREDS)
    assert client.request.await_count == 1
    assert "dav.example.com" not in str(raised.value)


async def test_fetch_sends_auth_and_depth_to_the_collection() -> None:
    client = _client(_http_response(207, _multistatus()))
    await CalDAVConnector(client=client).fetch_events(
        {"url": COLLECTION.rstrip("/"), "access_token": "t"}
    )
    args, kwargs = client.request.await_args
    assert args == ("REPORT", COLLECTION)
    assert kwargs["headers"]["Authorization"] == "Bearer t"
    assert kwargs["headers"]["Depth"] == "1"
    assert kwargs["auth"] is None


@pytest.mark.parametrize("status", [404, 410])
async def test_delete_of_an_absent_resource_is_complete(status: int) -> None:
    client = _client(_http_response(status))
    await CalDAVConnector(client=client).delete_event(CREDS, _event())
    assert client.delete.await_args.kwargs["headers"]["If-Match"] == '"etag-1"'


async def test_delete_with_a_changed_revision_is_a_conflict() -> None:
    client = _client(_http_response(412))
    with pytest.raises(CalendarConnectorError, match="412"):
        await CalDAVConnector(client=client).delete_event(CREDS, _event())


async def test_put_is_not_retried() -> None:
    current = _http_response(200, VEVENT.format(uid="uid-1").encode(), {"etag": '"etag-1"'})
    client = _client(current)
    client.put = AsyncMock(return_value=_http_response(503))
    with pytest.raises(CalendarConnectorError, match="Aktualisierung fehlgeschlagen"):
        await CalDAVConnector(client=client).update_event_times(
            CREDS,
            _event(),
            start_at=datetime(2026, 3, 1, 11, tzinfo=UTC),
            end_at=datetime(2026, 3, 1, 13, tzinfo=UTC),
        )
    assert client.put.await_count == 1


@pytest.mark.parametrize("operation", ["delete", "update", "exists"])
async def test_writes_and_probes_refuse_hrefs_outside_the_collection(operation: str) -> None:
    client = _client(_http_response(200))
    connector = CalDAVConnector(client=client)
    href = "https://dav.example.com/calendars/gemeinde/../other/uid-1.ics"
    with pytest.raises(CalendarConnectorError, match="außerhalb des Kalenders"):
        if operation == "delete":
            await connector.delete_event(CREDS, _event(resource_id=href))
        elif operation == "update":
            await connector.update_event_times(
                CREDS,
                _event(resource_id=href),
                start_at=datetime.now(UTC),
                end_at=datetime.now(UTC),
            )
        else:
            await connector.resource_exists(CREDS, href)
    client.get.assert_not_awaited()
    client.delete.assert_not_awaited()


@pytest.mark.parametrize(("status", "exists"), [(200, True), (404, False), (410, False)])
async def test_resource_exists_maps_missing_to_false(status: int, exists: bool) -> None:
    client = _client(_http_response(status))
    assert await CalDAVConnector(client=client).resource_exists(CREDS, "uid-1.ics") is exists
