# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""HTTP transport that caps a provider response while it is streamed (#605).

``client.get`` buffers the whole body before ``json()``; a single oversized or
compressed page could exhaust memory before any post-hoc size check ran. The
transport therefore

* asks for ``Accept-Encoding: identity`` and rejects compressed answers (a
  size cap on compressed bytes would not bound the decompressed size),
* rejects an oversized declared ``Content-Length`` up front, and
* aborts the stream as soon as more than ``max_bytes`` have been received.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from app.config import settings
from app.domain.ports.calendar import CalendarConnectorError


def _too_large() -> CalendarConnectorError:
    return CalendarConnectorError("Kalender-Antwort überschreitet das Limit für Datenmenge")


class _BoundedStream(httpx.AsyncByteStream):
    def __init__(self, inner: httpx.AsyncByteStream, max_bytes: int) -> None:
        self._inner = inner
        self._max_bytes = max_bytes

    async def __aiter__(self) -> AsyncIterator[bytes]:
        received = 0
        async for chunk in self._inner:
            received += len(chunk)
            if received > self._max_bytes:
                raise _too_large()
            yield chunk

    async def aclose(self) -> None:
        await self._inner.aclose()


class BoundedTransport(httpx.AsyncBaseTransport):
    def __init__(self, inner: httpx.AsyncBaseTransport, *, max_bytes: int) -> None:
        self._inner = inner
        self._max_bytes = max_bytes

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        request.headers["accept-encoding"] = "identity"
        response = await self._inner.handle_async_request(request)
        try:
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise CalendarConnectorError("Kalender-Antwort mit Komprimierung wird abgelehnt")
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > self._max_bytes:
                raise _too_large()
        except CalendarConnectorError:
            await response.aclose()
            raise
        assert isinstance(response.stream, httpx.AsyncByteStream)
        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            stream=_BoundedStream(response.stream, self._max_bytes),
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self._inner.aclose()


def make_bounded_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Client for paginated provider APIs with the configured per-response cap."""
    transport = BoundedTransport(
        httpx.AsyncHTTPTransport(), max_bytes=settings.sync_max_response_bytes
    )
    return httpx.AsyncClient(timeout=timeout, transport=transport)
