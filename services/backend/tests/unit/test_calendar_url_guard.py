# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

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
    "fec0::1",  # deprecated IPv6 site-local (is_global=True in Python)
    "feff::1",  # upper end of fec0::/10
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
    "::ffff:0:127.0.0.1",  # IPv4-translatable (SIIT, RFC 7915) loopback
    "::ffff:0:10.0.0.1",  # IPv4-translatable RFC1918
    "240.0.0.1",  # reserved
]


@pytest.fixture(autouse=True)
def _no_retry_backoff(monkeypatch):
    # Blocked and unreachable hosts are retried identically (no timing oracle);
    # skip the real backoff sleeps in tests.
    from tenacity import wait_none

    monkeypatch.setattr(
        "app.adapters.calendar.http_policy.wait_exponential_jitter", lambda **_: wait_none()
    )


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
        "https://localhost./feed.ics",
        "https://foo.localhost./feed.ics",
        "https://LOCALHOST./feed.ics",
        "https://Foo.LocalHost/feed.ics",
        "https://localhost../feed.ics",
        "https://127.0.0.1/feed.ics",
        "https://169.254.169.254/latest/meta-data",
        "https://10.1.2.3/feed.ics",
        "https://[::1]/feed.ics",
        "https://[fc00::1]/feed.ics",
        "https://[::ffff:127.0.0.1]/feed.ics",
        "https://[::ffff:0:127.0.0.1]/feed.ics",
        "https://[::ffff:0:10.0.0.1]/feed.ics",
        "https://[fec0::1]/feed.ics",
        # Legacy IPv4 literal forms that getaddrinfo()/inet_aton() resolve
        # without DNS: abbreviated, single integer, hex and octal.
        "https://127.1/feed.ics",
        "https://10.1/feed.ics",
        "https://2130706433/feed.ics",
        "https://0x7f.1/feed.ics",
        "https://0x7f000001/feed.ics",
        "https://0177.0.0.1/feed.ics",
        "https://0251.0376.0251.0376/feed.ics",
    ],
)
def test_validate_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeCalendarUrlError):
        validate_calendar_url(url)


def test_validate_accepts_public_https_url():
    validate_calendar_url("https://calendar.example.com/feed.ics")
    validate_calendar_url("https://93.184.216.34:8443/feed.ics")
    # Names that merely start with digits are hostnames, not IP literals.
    validate_calendar_url("https://1und1.example.com/feed.ics")


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
        with pytest.raises(httpx.ConnectError):
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


# ── review follow-ups (#463) ─────────────────────────────────────────────────


async def test_gzip_bomb_is_rejected_before_decompression():
    import gzip

    bomb = gzip.compress(b"\0" * (MAX_RESPONSE_BYTES + 1024 * 1024))
    assert len(bomb) < MAX_RESPONSE_BYTES // 100
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return httpx.Response(
            200,
            content=bomb,
            headers={"content-encoding": "gzip", "content-type": "text/calendar"},
        )

    connector = ICalConnector(client=_client(handler, "93.184.216.34"))
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"})
    assert seen[0].headers["accept-encoding"] == "identity"


async def test_identity_encoded_response_is_accepted():
    def handler(request):
        return httpx.Response(
            200, content=ICS, headers={"content-encoding": "identity", "content-type": "text/calendar"}
        )

    connector = ICalConnector(client=_client(handler, "93.184.216.34"))
    assert await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"}) == []


async def test_falls_back_to_next_validated_address_on_connect_error():
    tried: list[str] = []

    def handler(request):
        tried.append(request.url.host)
        if request.url.host == "93.184.216.34":
            raise httpx.ConnectError("unreachable", request=request)
        return _ok(request)

    connector = ICalConnector(
        client=_client(handler, "93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946")
    )
    await connector.fetch_events({"url": "https://calendar.example.com/feed.ics"})
    # each resilient_request attempt tries the first address, then falls back
    assert tried[:2] == ["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"]


async def test_fallback_never_leaves_the_validated_address_set():
    tried: list[str] = []

    def handler(request):
        tried.append(request.url.host)
        raise httpx.ConnectError("unreachable", request=request)

    transport = GuardedTransport(
        inner=httpx.MockTransport(handler), resolver=_resolver("93.184.216.34", "93.184.216.35")
    )
    async with guarded_client(transport=transport) as client:
        with pytest.raises(httpx.ConnectError):
            await client.get("https://calendar.example.com/feed.ics")
    assert tried == ["93.184.216.34", "93.184.216.35"]


async def test_address_fallbacks_share_one_connect_deadline():
    """Several black-holed addresses must not each get the full connect timeout."""
    import asyncio
    import time

    budgets: list[float] = []

    class BlackHole(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            connect = request.extensions["timeout"]["connect"]
            budgets.append(connect)
            await asyncio.sleep(connect)
            raise httpx.ConnectTimeout("timed out", request=request)

    transport = GuardedTransport(
        inner=BlackHole(),
        resolver=_resolver("93.184.216.34", "93.184.216.35", "93.184.216.36", "93.184.216.37"),
    )
    async with httpx.AsyncClient(
        transport=transport, timeout=httpx.Timeout(5.0, connect=0.2), trust_env=False
    ) as client:
        started = time.monotonic()
        with pytest.raises(httpx.ConnectTimeout):
            await client.get("https://calendar.example.com/feed.ics")
        elapsed = time.monotonic() - started

    assert elapsed < 0.35  # one 0.2 s budget, not 4 x 0.2 s
    assert budgets[0] <= 0.2
    assert all(later < budgets[0] for later in budgets[1:])


async def test_slow_dns_resolution_is_bounded_by_connect_timeout():
    import asyncio

    async def slow_resolver(host, port):
        await asyncio.sleep(5)
        return ["93.184.216.34"]

    transport = GuardedTransport(inner=httpx.MockTransport(_ok), resolver=slow_resolver)
    async with httpx.AsyncClient(
        transport=transport, timeout=httpx.Timeout(5.0, connect=0.05), trust_env=False
    ) as client:
        with pytest.raises(httpx.ConnectTimeout):
            await client.get("https://calendar.example.com/feed.ics")


async def test_blocked_dns_answer_is_indistinguishable_from_unresolvable_host():
    """No internal-DNS oracle via trigger_sync / last_sync_error (finding 7)."""

    async def unresolvable(host, port):
        raise OSError("Name or service not known")

    def message(connector_cls, resolver, creds):
        async def run():
            transport = GuardedTransport(inner=httpx.MockTransport(_ok), resolver=resolver)
            connector = connector_cls(client=guarded_client(transport=transport))
            with pytest.raises(CalendarConnectorError) as exc_info:
                await connector.fetch_events(creds)
            return str(exc_info.value)

        return run()

    ics = {"url": "https://intranet.example.com/feed.ics"}
    dav = {"url": "https://intranet.example.com/cal/", "username": "u", "password": "p"}
    for connector_cls, creds in ((ICalConnector, ics), (CalDAVConnector, dav)):
        blocked = await message(connector_cls, _resolver("10.0.0.8"), creds)
        missing = await message(connector_cls, unresolvable, creds)
        assert blocked == missing


# ── NAT64 network-specific prefixes (RFC 6052), finding B ────────────────────

import ipaddress  # noqa: E402

from app.adapters.calendar.url_guard import _embedded_ipv4, _is_public  # noqa: E402
from app.config import settings  # noqa: E402

# RFC 6052 section 2.4 examples: 192.0.2.33 embedded under each prefix length.
RFC6052_EXAMPLES = {
    "2001:db8::/32": "2001:db8:c000:221::",
    "2001:db8:100::/40": "2001:db8:1c0:2:21::",
    "2001:db8:122::/48": "2001:db8:122:c000:2:2100::",
    "2001:db8:122:300::/56": "2001:db8:122:3c0:0:221::",
    "2001:db8:122:344::/64": "2001:db8:122:344:c0:2:2100:0",
    "2001:db8:122:344::/96": "2001:db8:122:344::c000:221",
}


def _synthesize(prefix: str, ipv4: str) -> str:
    """Embed ipv4 under prefix per RFC 6052 (u-octet = byte 8 stays zero)."""
    net = ipaddress.ip_network(prefix)
    out = bytearray(net.network_address.packed)
    slots = [i for i in range(net.prefixlen // 8, 16) if i != 8][:4]
    for slot, byte in zip(slots, ipaddress.IPv4Address(ipv4).packed, strict=True):
        out[slot] = byte
    return str(ipaddress.IPv6Address(bytes(out)))


@pytest.mark.parametrize(("prefix", "expected"), RFC6052_EXAMPLES.items())
def test_synthesizer_matches_rfc6052_examples(prefix, expected):
    assert ipaddress.IPv6Address(_synthesize(prefix, "192.0.2.33")) == ipaddress.IPv6Address(
        expected
    )


@pytest.mark.parametrize("prefix", list(RFC6052_EXAMPLES))
@pytest.mark.parametrize("embedded", ["10.0.0.1", "127.0.0.1", "169.254.169.254"])
def test_configured_nat64_prefix_with_internal_ipv4_is_rejected(monkeypatch, prefix, embedded):
    address = _synthesize(prefix, embedded)
    monkeypatch.setattr(settings, "calendar_nat64_prefixes", prefix)
    assert _is_public(address) is False


@pytest.mark.parametrize("prefix", list(RFC6052_EXAMPLES))
def test_configured_nat64_prefix_with_public_ipv4_is_accepted(monkeypatch, prefix):
    monkeypatch.setattr(settings, "calendar_nat64_prefixes", prefix)
    assert _is_public(_synthesize(prefix, "93.184.216.34")) is True


def test_overlapping_nat64_prefixes_require_every_embedding_to_be_public(monkeypatch):
    monkeypatch.setattr(settings, "calendar_nat64_prefixes", "2001:db8::/32,2001:db8:a00:1::/96")
    address = _synthesize("2001:db8:a00:1::/96", "93.184.216.34")
    # Public under the /96, but read as 10.0.0.1 under the /32: fail closed.
    assert str(_embedded_ipv4(ipaddress.IPv6Address(address), ipaddress.IPv6Network("2001:db8::/32"))) == "10.0.0.1"
    assert _is_public(address) is False


def test_unconfigured_network_specific_prefix_is_not_unwrapped():
    # Without configuration the address is judged as plain IPv6 (2001:db8::/32
    # is documentation space, hence not global).
    assert settings.calendar_nat64_prefixes == ""
    assert _is_public(_synthesize("2001:db8:122:344::/96", "93.184.216.34")) is False


@pytest.mark.parametrize("prefix", ["64:ff9b::/96", "64:ff9b:1::/48"])
def test_well_known_nat64_prefixes_are_always_unwrapped(prefix):
    assert _is_public(_synthesize(prefix, "10.0.0.1")) is False
    assert _is_public(_synthesize(prefix, "93.184.216.34")) is True


@pytest.mark.parametrize(("prefix", "address"), RFC6052_EXAMPLES.items())
def test_embedded_ipv4_extraction_matches_rfc6052_examples(prefix, address):
    extracted = _embedded_ipv4(ipaddress.IPv6Address(address), ipaddress.IPv6Network(prefix))
    assert str(extracted) == "192.0.2.33"


# ── One hard time budget per fetch (#486: never longer than 30 s) ────────────


class _Stall(httpx.AsyncBaseTransport):
    """Accepts the TCP connect, then never finishes (e.g. a stalled TLS handshake)."""

    def __init__(self) -> None:
        self.attempts = 0

    async def handle_async_request(self, request):
        import asyncio

        self.attempts += 1
        await asyncio.sleep(3600)


async def _elapsed(transport, url="https://calendar.example.com/feed.ics"):
    import time

    async with httpx.AsyncClient(
        transport=transport, timeout=httpx.Timeout(5.0), trust_env=False
    ) as client:
        started = time.monotonic()
        with pytest.raises(httpx.TimeoutException):
            response = await client.get(url)
            await response.aread()
        return time.monotonic() - started


async def test_stalled_handshakes_on_every_address_stay_within_the_budget():
    stall = _Stall()
    transport = GuardedTransport(
        inner=stall,
        resolver=_resolver("93.184.216.34", "93.184.216.35", "93.184.216.36"),
        budget_seconds=0.3,
    )
    assert await _elapsed(transport) < 0.45  # not 3 x connect, not 3 x read
    assert stall.attempts == 1  # a timed-out attempt ends the fetch: budget used up


async def test_slowly_trickling_body_stays_within_the_budget():
    import asyncio

    async def drip():
        for _ in range(100):
            await asyncio.sleep(0.05)  # each chunk is far below httpx's 5 s read timeout
            yield b"x"

    def handler(request):
        return httpx.Response(200, stream=_AsyncStream(drip()))

    transport = GuardedTransport(
        inner=httpx.MockTransport(handler), resolver=_resolver("93.184.216.34"), budget_seconds=0.3
    )
    assert await _elapsed(transport) < 0.45


class _AsyncStream(httpx.AsyncByteStream):
    def __init__(self, gen) -> None:
        self._gen = gen

    async def __aiter__(self):
        async for chunk in self._gen:
            yield chunk


async def test_retries_share_one_budget(monkeypatch):
    import asyncio
    import time

    from app.adapters.calendar import http_policy

    monkeypatch.setattr(http_policy, "REQUEST_BUDGET_SECONDS", 0.3)
    calls = 0

    async def flaky():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.2)
        raise httpx.ConnectTimeout("timed out")

    started = time.monotonic()
    with pytest.raises(CalendarConnectorError):
        await http_policy.resilient_request(flaky, provider="iCal")
    assert time.monotonic() - started < 0.45
    assert calls <= 2


async def test_fallback_after_a_refused_address_is_bounded_by_both_deadlines():
    """Fallback still happens, and the stalled second address ends at the budget."""
    import asyncio
    import time

    tried: list[str] = []

    class RefuseThenStall(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            tried.append(request.url.host)
            if request.url.host == "93.184.216.34":
                await asyncio.sleep(0.05)
                raise httpx.ConnectError("refused", request=request)
            await asyncio.sleep(3600)  # TCP accepted, TLS never completes

    transport = GuardedTransport(
        inner=RefuseThenStall(),
        resolver=_resolver("93.184.216.34", "93.184.216.35"),
        budget_seconds=0.3,
    )
    async with httpx.AsyncClient(
        transport=transport, timeout=httpx.Timeout(5.0, connect=5.0), trust_env=False
    ) as client:
        started = time.monotonic()
        with pytest.raises(httpx.TimeoutException):
            await client.get("https://calendar.example.com/feed.ics")
        elapsed = time.monotonic() - started

    assert tried == ["93.184.216.34", "93.184.216.35"]  # fell back to the validated second IP
    assert elapsed < 0.45  # total budget, although connect=5 s per attempt
