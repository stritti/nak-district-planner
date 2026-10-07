"""SSRF hardening for outbound calendar fetching (issue #463).

No network: DNS resolution is injected and the real socket transport is
replaced by ``httpx.MockTransport`` behind the guard.
"""

from __future__ import annotations

import httpx
import pytest

from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.ical_connector import ICalConnector
from app.adapters.calendar.url_guard import (
    MAX_RESPONSE_BYTES,
    GuardedTransport,
    UnsafeCalendarUrlError,
    guarded_client,
    validate_calendar_url,
)
from app.domain.ports.calendar import CalendarConnectorError

ICS = b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//T//EN\r\nEND:VCALENDAR\r\n"

BLOCKED_ADDRESSES = [
    "127.0.0.1",  # loopback
    "169.254.169.254",  # link-local / cloud metadata
    "10.0.0.5",  # RFC1918
    "172.16.3.4",  # RFC1918
    "192.168.1.1",  # RFC1918
    "100.64.0.1",  # carrier-grade NAT
    "0.0.0.0",
    "::1",  # IPv6 loopback
    "fc00::1",  # IPv6 ULA
    "fd12:3456::1",  # IPv6 ULA
    "fe80::1",  # IPv6 link-local
    "::ffff:127.0.0.1",  # IPv4-mapped loopback
    "::ffff:10.0.0.1",  # IPv4-mapped RFC1918
    "64:ff9b::a9fe:a9fe",  # NAT64 of 169.254.169.254
    "2002:7f00:1::1",  # 6to4 of 127.0.0.1
]


def _resolver(*addresses: str):
    async def resolve(host: str, port: int) -> list[str]:
        return list(addresses)

    return resolve


def _client(handler, *addresses: str, follow_redirects: bool = False) -> httpx.AsyncClient:
    transport = GuardedTransport(
        inner=httpx.MockTransport(handler), resolver=_resolver(*addresses)
    )
    return guarded_client(transport=transport, follow_redirects=follow_redirects)


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=ICS, headers={"content-type": "text/calendar"})


# ── static URL validation (API create/update) ────────────────────────────────


@pytest.mark.parametrize(
    "url",
    [
        "http://calendar.example.com/feed.ics",
        "ftp://calendar.example.com/feed.ics",
        "file:///etc/passwd",
        "https://user:secret@calendar.example.com/feed.ics",  # ggignore - fake test credentials
        "https:///feed.ics",
        "not a url",
        "",
        None,
        42,
        "https://localhost/feed.ics",
        "https://127.0.0.1/feed.ics",
        "https://169.254.169.254/latest/meta-data",
        "https://10.1.2.3/feed.ics",
        "https://[::1]/feed.ics",
        "https://[fc00::1]/feed.ics",
        "https://[::ffff:127.0.0.1]/feed.ics",
    ],
)
def test_validate_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeCalendarUrlError):
        validate_calendar_url(url)


def test_validate_accepts_public_https_url():
    validate_calendar_url("https://calendar.example.com/feed.ics")
    validate_calendar_url("https://93.184.216.34:8443/feed.ics")


def test_validate_allows_http_and_local_only_with_dev_opt_in():
    validate_calendar_url("http://localhost:5232/cal/", allow_insecure=True)
    with pytest.raises(UnsafeCalendarUrlError):
        validate_calendar_url("https://user:pw@localhost/cal/", allow_insecure=True)  # ggignore - fake test credentials


def test_error_message_does_not_echo_url():
    with pytest.raises(UnsafeCalendarUrlError) as exc_info:
        validate_calendar_url("https://user:topsecret@10.0.0.1/feed.ics")  # ggignore - fake test credentials
    assert "topsecret" not in str(exc_info.value)
    assert "10.0.0.1" not in str(exc_info.value)


# ── connection-time checks (every request) ───────────────────────────────────


@pytest.mark.parametrize("address", BLOCKED_ADDRESSES)
async def test_transport_blocks_hosts_resolving_to_internal_addresses(address):
    calls: list[httpx.Request] = []

    def handler(request):
        calls.append(request)
        return _ok(request)

    connector = ICalConnector(client=_client(handler, address))
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"})
    assert calls == []


async def test_transport_blocks_if_any_resolved_address_is_internal():
    calls: list[httpx.Request] = []
    connector = ICalConnector(
        client=_client(lambda r: calls.append(r) or _ok(r), "93.184.216.34", "127.0.0.1")
    )
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"})
    assert calls == []


async def test_transport_rejects_plain_http_without_dev_opt_in():
    calls: list[httpx.Request] = []
    connector = ICalConnector(client=_client(lambda r: calls.append(r) or _ok(r), "93.184.216.34"))
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events({"url": "http://calendar.example.com/feed.ics"})
    assert calls == []


async def test_transport_pins_validated_ip_and_preserves_host_and_sni():
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return _ok(request)

    connector = ICalConnector(client=_client(handler, "93.184.216.34"))
    await connector.fetch_events({"url": "https://calendar.example.com:8443/feed.ics"})

    (request,) = seen
    assert request.url.host == "93.184.216.34"
    assert request.url.port == 8443
    assert request.headers["host"] == "calendar.example.com:8443"
    assert request.extensions["sni_hostname"] == "calendar.example.com"


async def test_ical_does_not_follow_redirect_to_internal_host():
    calls: list[httpx.Request] = []

    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"location": "http://127.0.0.1:6379/"})

    connector = ICalConnector(client=_client(handler, "93.184.216.34"))
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"})
    assert len(calls) == 1


async def test_every_redirect_hop_is_revalidated_even_if_redirects_are_enabled():
    resolved: dict[str, str] = {"calendar.example.com": "93.184.216.34", "evil.example": "10.0.0.1"}
    calls: list[str] = []

    async def resolve(host, port):
        return [resolved[host]]

    def handler(request):
        calls.append(request.headers["host"])
        return httpx.Response(302, headers={"location": "https://evil.example/x"})

    transport = GuardedTransport(inner=httpx.MockTransport(handler), resolver=resolve)
    async with guarded_client(transport=transport, follow_redirects=True) as client:
        with pytest.raises(UnsafeCalendarUrlError):
            await client.get("https://calendar.example.com/feed.ics")
    assert calls == ["calendar.example.com"]


async def test_oversized_streamed_response_is_aborted():
    chunk = b"x" * 1024 * 1024

    async def body():
        for _ in range(MAX_RESPONSE_BYTES // len(chunk) + 2):
            yield chunk

    connector = ICalConnector(
        client=_client(lambda r: httpx.Response(200, content=body()), "93.184.216.34")
    )
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"})


async def test_oversized_content_length_is_rejected_before_reading():
    def handler(request):
        return httpx.Response(
            200, headers={"content-length": str(MAX_RESPONSE_BYTES + 1)}, content=b""
        )

    connector = ICalConnector(client=_client(handler, "93.184.216.34"))
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"})


async def test_caldav_is_guarded_as_well():
    calls: list[httpx.Request] = []
    connector = CalDAVConnector(client=_client(lambda r: calls.append(r) or _ok(r), "10.0.0.7"))
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events(
            {"url": "https://dav.example.com/cal/", "username": "u", "password": "p"}  # ggignore - fake test credentials
        )
    assert calls == []


def test_default_connector_clients_are_guarded_without_redirects_or_env_proxies():
    for connector in (ICalConnector(), CalDAVConnector()):
        client = connector._client
        assert client.follow_redirects is False
        assert client.trust_env is False
        assert isinstance(client._transport, GuardedTransport)


# ── generic error messages (no oracle, no secrets) ───────────────────────────


@pytest.mark.parametrize("status", [401, 404, 500])
async def test_ical_status_and_transport_errors_share_one_generic_message(status):
    def status_handler(request):
        return httpx.Response(status)

    def transport_handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    messages = []
    for handler in (status_handler, transport_handler):
        connector = ICalConnector(client=_client(handler, "93.184.216.34"))
        with pytest.raises(CalendarConnectorError) as exc_info:
            await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"})
        messages.append(str(exc_info.value))
    assert messages[0] == messages[1]
    assert str(status) not in messages[0]


@pytest.mark.parametrize("status", [401, 500])
async def test_caldav_error_contains_neither_url_nor_credentials(status):
    connector = CalDAVConnector(
        client=_client(lambda r: httpx.Response(status), "93.184.216.34")
    )
    with pytest.raises(CalendarConnectorError) as exc_info:
        await connector.fetch_events(
            {
                "url": "https://dav.example.com/secret-path-token/",
                "username": "alice",
                "password": "hunter2",  # ggignore - fake test credentials
            }
        )
    message = str(exc_info.value)
    for leaked in ("dav.example.com", "secret-path-token", "alice", "hunter2", str(status)):
        assert leaked not in message
