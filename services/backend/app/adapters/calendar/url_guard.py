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
import socket
from collections.abc import AsyncIterator, Awaitable, Callable

import httpx

from app.config import settings
from app.domain.ports.calendar import CalendarConnectorError

MAX_RESPONSE_BYTES = 10 * 1024 * 1024
_NAT64 = ipaddress.ip_network("64:ff9b::/96")

Resolver = Callable[[str, int], Awaitable[list[str]]]


class UnsafeCalendarUrlError(CalendarConnectorError):
    """The calendar URL or its resolved address is not allowed."""


class ResponseTooLargeError(CalendarConnectorError):
    """The calendar response exceeded MAX_RESPONSE_BYTES."""


class UnsupportedContentEncodingError(CalendarConnectorError):
    """The server compressed the response although identity was requested."""


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        elif ip.sixtofour is not None:
            ip = ip.sixtofour
        elif ip in _NAT64:
            ip = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip.is_global and not ip.is_multicast


def _ip_literal(host: str) -> str | None:
    try:
        return str(ipaddress.ip_address(host.strip("[]")))
    except ValueError:
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
    literal = _ip_literal(url.host)
    if url.host == "localhost" or url.host.endswith(".localhost") or (
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


class _CappedStream(httpx.AsyncByteStream):
    def __init__(self, stream: httpx.AsyncByteStream) -> None:
        self._stream = stream

    async def __aiter__(self) -> AsyncIterator[bytes]:
        total = 0
        async for chunk in self._stream:
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
    ) -> None:
        # No keep-alive: a pooled connection is keyed by the pinned IP and
        # must not be reused for a different hostname/SNI.
        self._inner = inner or httpx.AsyncHTTPTransport(
            limits=httpx.Limits(max_keepalive_connections=0)
        )
        self._resolve = resolver or _system_resolver
        self._allow_insecure = (
            settings.calendar_allow_insecure_urls if allow_insecure is None else allow_insecure
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        _check_url(request.url, self._allow_insecure)
        # Request uncompressed bodies and refuse anything else below: httpx
        # decodes after the transport, so a compressed body would bypass the
        # size cap (decompression bomb).
        request.headers["Accept-Encoding"] = "identity"
        if not self._allow_insecure:
            host = request.url.host
            port = request.url.port or (443 if request.url.scheme == "https" else 80)
            try:
                addresses = await self._resolve(host, port)
            except OSError as exc:
                raise httpx.ConnectError("Name resolution failed", request=request) from exc
            if not addresses or not all(_is_public(a) for a in addresses):
                raise UnsafeCalendarUrlError("Kalender-URL zeigt auf ein nicht erlaubtes Netz")
            if _ip_literal(host) is None:
                # Connect to the validated IP; the copied Host header and the
                # SNI extension keep virtual hosting and cert checks intact.
                request = httpx.Request(
                    request.method,
                    request.url.copy_with(host=addresses[0].split("%", 1)[0]),
                    headers=request.headers,
                    stream=request.stream,
                    extensions={**request.extensions, "sni_hostname": host},
                )

        response = await self._inner.handle_async_request(request)
        if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
            await response.aclose()
            raise UnsupportedContentEncodingError("Kalender-Antwort ist komprimiert")
        length = response.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_RESPONSE_BYTES:
            await response.aclose()
            raise ResponseTooLargeError("Kalender-Antwort ist zu groß")
        response.stream = _CappedStream(response.stream)  # type: ignore[arg-type]
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
        timeout=30.0,
        follow_redirects=follow_redirects,
        trust_env=False,
    )
