"""SSRF guard for outbound calendar requests (issue #463).

Two layers:

* ``validate_calendar_url`` — static check at API create/update (scheme,
  host, no embedded credentials, IP literals must be public). No DNS lookup,
  so the request path never depends on resolver behaviour.
* ``GuardedTransport`` — authoritative check on *every* request, including
  redirect hops: the host is resolved once, every returned address must be
  public, and the connection is then made to that validated IP (Host header
  and TLS SNI/certificate check keep the original hostname). Pinning the IP
  closes the DNS-rebinding window between check and connect. Responses are
  capped at ``MAX_RESPONSE_BYTES`` while streaming.

``CALENDAR_ALLOW_INSECURE_URLS`` (dev only, rejected by ``production_guard``)
turns off the scheme/address checks for local test servers.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from collections.abc import AsyncIterator, Awaitable, Callable

import httpx

from app.config import settings
from app.domain.ports.calendar import CalendarConnectorError

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 10 * 1024 * 1024
# Hard upper bound for one calendar fetch: DNS, every connect/TLS attempt,
# response headers and body together (and all retries, see http_policy).
REQUEST_BUDGET_SECONDS = 30.0
_DEFAULT_DNS_TIMEOUT = 10.0
# Prefixes that embed an IPv4 address (RFC 6052 layout): the well-known and
# local-use NAT64 prefixes and IPv4-translatable SIIT addresses (RFC 7915,
# reported as is_global by Python). Deployments add their network-specific
# NAT64 prefixes via CALENDAR_NAT64_PREFIXES.
_BUILTIN_EMBEDDED_IPV4 = (
    ipaddress.IPv6Network("64:ff9b::/96"),
    ipaddress.IPv6Network("64:ff9b:1::/48"),
    ipaddress.IPv6Network("::ffff:0:0/96"),
)

Resolver = Callable[[str, int], Awaitable[list[str]]]


class UnsafeCalendarUrlError(CalendarConnectorError):
    """The calendar URL or its resolved address is not allowed."""


class BlockedAddressError(httpx.ConnectError):
    """The host resolved to a non-public address.

    Deliberately a transport error: callers see the same generic message as
    for an unresolvable or unreachable host, so the sync endpoint and
    last_sync_error cannot be used as an internal-DNS oracle.
    """


class ResponseTooLargeError(CalendarConnectorError):
    """The calendar response exceeded MAX_RESPONSE_BYTES."""


class UnsupportedContentEncodingError(CalendarConnectorError):
    """The server compressed the response although identity was requested."""


def _embedded_ipv4(
    ip: ipaddress.IPv6Address, prefix: ipaddress.IPv6Network
) -> ipaddress.IPv4Address:
    """Extract the IPv4 address per RFC 6052 section 2.2 (skipping the u-octet, bits 64-71)."""
    packed = ip.packed
    slots = [i for i in range(prefix.prefixlen // 8, 16) if i != 8][:4]
    return ipaddress.IPv4Address(bytes(packed[i] for i in slots))


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # Python reports the deprecated IPv6 site-local range (fec0::/10) as global.
    site_local = isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local
    return ip.is_global and not (ip.is_multicast or ip.is_reserved or site_local)


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv4Address):
        return _is_public_ip(ip)
    if ip.ipv4_mapped is not None:
        return _is_public_ip(ip.ipv4_mapped)
    if ip.sixtofour is not None:
        return _is_public_ip(ip.sixtofour)
    prefixes = [
        p for p in _BUILTIN_EMBEDDED_IPV4 + settings.calendar_nat64_networks if ip in p
    ]
    if prefixes:
        # Overlapping prefixes: every possible embedded IPv4 must be public.
        return all(_is_public_ip(_embedded_ipv4(ip, p)) for p in prefixes)
    return _is_public_ip(ip)


def _ip_literal(host: str) -> str | None:
    try:
        return str(ipaddress.ip_address(host.strip("[]")))
    except ValueError:
        pass
    # Legacy IPv4 forms ("127.1", "2130706433", "0x7f.1") are not valid for
    # ipaddress but getaddrinfo() resolves them without DNS; treat them as the
    # IPv4 address they denote. Real hostnames never parse with inet_aton().
    try:
        return str(ipaddress.IPv4Address(socket.inet_aton(host)))
    except OSError:
        return None


def _check_url(url: httpx.URL, allow_insecure: bool) -> None:
    allowed = {"https", "http"} if allow_insecure else {"https"}
    if url.scheme not in allowed:
        raise UnsafeCalendarUrlError("Kalender-URL muss HTTPS verwenden")
    if not url.host:
        raise UnsafeCalendarUrlError("Kalender-URL ohne Host")
    if url.userinfo:
        raise UnsafeCalendarUrlError(
            "Zugangsdaten dürfen nicht in der Kalender-URL stehen"
        )
    if allow_insecure:
        return
    # httpx already lowercases and IDNA-encodes the host; strip trailing dots
    # so "localhost." (FQDN form) cannot bypass the name check.
    host = url.host.lower().rstrip(".")
    literal = _ip_literal(host)
    if host == "localhost" or host.endswith(".localhost") or (
        literal is not None and not _is_public(literal)
    ):
        raise UnsafeCalendarUrlError("Kalender-URL zeigt auf ein nicht erlaubtes Netz")


def validate_calendar_url(url: object, *, allow_insecure: bool | None = None) -> None:
    """Static validation for user-supplied calendar URLs. Never echoes the URL."""
    if allow_insecure is None:
        allow_insecure = settings.calendar_allow_insecure_urls
    if not isinstance(url, str) or not url:
        raise UnsafeCalendarUrlError("Kalender-URL fehlt")
    try:
        parsed = httpx.URL(url)
    except (httpx.InvalidURL, TypeError, ValueError):
        raise UnsafeCalendarUrlError("Kalender-URL ist ungültig") from None
    _check_url(parsed, allow_insecure)


async def _system_resolver(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def _budget_exceeded(request: httpx.Request) -> httpx.TimeoutException:
    return httpx.TimeoutException("Calendar request exceeded its time budget", request=request)


class _CappedStream(httpx.AsyncByteStream):
    """Caps the body size and keeps reading within the request deadline."""

    def __init__(self, stream: httpx.AsyncByteStream, request: httpx.Request, deadline: float) -> None:
        self._stream = stream
        self._request = request
        self._deadline = deadline

    async def __aiter__(self) -> AsyncIterator[bytes]:
        total = 0
        loop = asyncio.get_running_loop()
        chunks = aiter(self._stream)
        while True:
            try:
                chunk = await asyncio.wait_for(anext(chunks), self._deadline - loop.time())
            except StopAsyncIteration:
                return
            except TimeoutError as exc:
                raise _budget_exceeded(self._request) from exc
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise ResponseTooLargeError("Kalender-Antwort ist zu groß")
            yield chunk

    async def aclose(self) -> None:
        await self._stream.aclose()


class GuardedTransport(httpx.AsyncBaseTransport):
    """Validate, resolve-and-pin, and size-cap every outbound request."""

    def __init__(
        self,
        *,
        inner: httpx.AsyncBaseTransport | None = None,
        resolver: Resolver | None = None,
        allow_insecure: bool | None = None,
        budget_seconds: float = REQUEST_BUDGET_SECONDS,
    ) -> None:
        # No keep-alive: a pooled connection is keyed by the pinned IP and
        # must not be reused for a different hostname/SNI.
        self._inner = inner or httpx.AsyncHTTPTransport(
            limits=httpx.Limits(max_keepalive_connections=0)
        )
        self._resolve = resolver or _system_resolver
        self._budget = budget_seconds
        self._allow_insecure = (
            settings.calendar_allow_insecure_urls if allow_insecure is None else allow_insecure
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        _check_url(request.url, self._allow_insecure)
        # Request uncompressed bodies and refuse anything else below: httpx
        # decodes after the transport, so a compressed body would bypass the
        # size cap (decompression bomb).
        request.headers["Accept-Encoding"] = "identity"
        loop = asyncio.get_running_loop()
        # Everything below (DNS, every connect/TLS attempt, headers, body)
        # shares one deadline; httpx timeouts only bound single operations.
        budget_deadline = loop.time() + self._budget
        if self._allow_insecure or _ip_literal(request.url.host) is not None:
            # IP literals were fully validated by _check_url (or dev opt-in).
            return await self._attempt(request, request, budget_deadline)

        host = request.url.host
        port = request.url.port or (443 if request.url.scheme == "https" else 80)
        # One connect deadline covers DNS resolution and every address fallback,
        # so black-holed answers cannot multiply the configured timeout.
        timeouts = request.extensions.get("timeout") or {}
        deadline = min(
            loop.time() + (timeouts.get("connect") or _DEFAULT_DNS_TIMEOUT), budget_deadline
        )
        try:
            addresses = await asyncio.wait_for(self._resolve(host, port), deadline - loop.time())
        except TimeoutError as exc:
            raise httpx.ConnectTimeout("Name resolution timed out", request=request) from exc
        except OSError as exc:
            raise httpx.ConnectError("Name resolution failed", request=request) from exc
        if not addresses or not all(_is_public(a) for a in addresses):
            logger.warning("Calendar request blocked: host resolved to a non-public address")
            raise BlockedAddressError("Blocked address", request=request)

        # Connect only to the validated IPs (in resolver order, falling back on
        # connect failures); the copied Host header and the SNI extension keep
        # virtual hosting and certificate checks bound to the hostname.
        last_error: httpx.TransportError | None = None
        for address in dict.fromkeys(a.split("%", 1)[0] for a in addresses):
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise httpx.ConnectTimeout("Connect timed out", request=request)
            pinned = httpx.Request(
                request.method,
                request.url.copy_with(host=address),
                headers=request.headers,
                stream=request.stream,
                extensions={
                    **request.extensions,
                    "timeout": {**timeouts, "connect": remaining},
                    "sni_hostname": host,
                },
            )
            try:
                return await self._attempt(request, pinned, budget_deadline)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                last_error = exc
                continue
        assert last_error is not None  # noqa: S101 - loop ran at least once
        raise last_error

    async def _attempt(
        self, request: httpx.Request, outgoing: httpx.Request, budget_deadline: float
    ) -> httpx.Response:
        """One connection attempt (TCP, TLS, headers) within the request budget."""
        remaining = budget_deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise _budget_exceeded(request)
        try:
            response = await asyncio.wait_for(self._inner.handle_async_request(outgoing), remaining)
        except TimeoutError as exc:
            raise _budget_exceeded(request) from exc
        return await self._checked(response, request, budget_deadline)

    async def _checked(
        self, response: httpx.Response, request: httpx.Request, deadline: float
    ) -> httpx.Response:
        if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
            await response.aclose()
            raise UnsupportedContentEncodingError("Kalender-Antwort ist komprimiert")
        length = response.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_RESPONSE_BYTES:
            await response.aclose()
            raise ResponseTooLargeError("Kalender-Antwort ist zu groß")
        response.stream = _CappedStream(response.stream, request, deadline)  # type: ignore[arg-type]
        return response

    async def aclose(self) -> None:
        await self._inner.aclose()


def guarded_client(
    *, transport: httpx.AsyncBaseTransport | None = None, follow_redirects: bool = False
) -> httpx.AsyncClient:
    """HTTP client for user-supplied calendar URLs.

    ``trust_env=False`` keeps environment proxies from bypassing the guard.
    """
    return httpx.AsyncClient(
        transport=transport or GuardedTransport(),
        timeout=REQUEST_BUDGET_SECONDS,
        follow_redirects=follow_redirects,
        trust_env=False,
    )
