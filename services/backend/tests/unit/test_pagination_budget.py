# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Provider-agnostic resource budget for paginated calendar fetches (#605)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapters.calendar.google_connector import GoogleCalendarConnector
from app.adapters.calendar.microsoft_connector import MicrosoftGraphCalendarConnector
from app.adapters.calendar.pagination_budget import PaginationBudget
from app.domain.ports.calendar import CalendarConnectorError

CREDS = {"access_token": "token"}


def _budget(**overrides) -> PaginationBudget:
    limits = {"max_pages": 3, "max_items": 10, "max_bytes": 1000, "max_seconds": 60.0}
    return PaginationBudget(**{**limits, **overrides})


def test_accepts_traffic_within_limits() -> None:
    budget = _budget()
    budget.charge(items=5, size_bytes=100, next_token="a")
    budget.charge(items=5, size_bytes=100, next_token=None)


def test_page_limit() -> None:
    budget = _budget()
    for token in ("a", "b"):
        budget.charge(items=0, size_bytes=0, next_token=token)
    with pytest.raises(CalendarConnectorError, match="Seiten"):
        budget.charge(items=0, size_bytes=0, next_token="c")
        budget.charge(items=0, size_bytes=0, next_token="d")


def test_item_limit() -> None:
    with pytest.raises(CalendarConnectorError, match="Einträge"):
        _budget().charge(items=11, size_bytes=0, next_token=None)


def test_byte_limit() -> None:
    budget = _budget()
    budget.charge(items=0, size_bytes=600, next_token="a")
    with pytest.raises(CalendarConnectorError, match="Datenmenge"):
        budget.charge(items=0, size_bytes=401, next_token=None)


def test_repeated_token_is_a_loop() -> None:
    budget = _budget(max_pages=10)
    budget.charge(items=0, size_bytes=0, next_token="same")
    with pytest.raises(CalendarConnectorError, match="wiederholt"):
        budget.charge(items=0, size_bytes=0, next_token="same")


def test_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr("app.adapters.calendar.pagination_budget.time.monotonic", lambda: now[0])
    budget = _budget(max_seconds=30.0)
    budget.charge(items=0, size_bytes=0, next_token="a")
    now[0] += 31
    with pytest.raises(CalendarConnectorError, match="Zeitbudget"):
        budget.charge(items=0, size_bytes=0, next_token="b")


def _response(data: dict, size: int = 10) -> MagicMock:
    response = MagicMock()
    response.json.return_value = data
    response.content = b"x" * size
    response.headers = {"content-type": "application/json"}
    response.raise_for_status.return_value = None
    return response


def _client(*responses: MagicMock) -> MagicMock:
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=list(responses))
    return client


async def test_google_repeated_page_token_aborts_instead_of_looping() -> None:
    page = _response({"items": [], "nextPageToken": "loop"})
    client = _client(*[page] * 50)
    connector = GoogleCalendarConnector(client=client, budget_factory=lambda: _budget(max_pages=50))
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events(CREDS)
    assert client.get.await_count == 2  # second page repeats the token


async def test_google_total_items_are_bounded_across_pages() -> None:
    items = [{"id": str(i)} for i in range(6)]
    client = _client(
        _response({"items": items, "nextPageToken": "a"}),
        _response({"items": items, "nextPageToken": "b"}),
    )
    connector = GoogleCalendarConnector(client=client, budget_factory=lambda: _budget())
    with pytest.raises(CalendarConnectorError, match="Einträge"):
        await connector.fetch_events(CREDS)


async def test_google_later_page_failure_returns_nothing_partial() -> None:
    first = _response({"items": [{"id": "1"}], "nextPageToken": "a"})
    client = _client(first, httpx.ConnectError("down"), httpx.ConnectError("down"), httpx.ConnectError("down"))
    connector = GoogleCalendarConnector(client=client, budget_factory=lambda: _budget())
    with pytest.raises(CalendarConnectorError):
        await connector.fetch_events(CREDS)


async def test_microsoft_uses_the_same_budget() -> None:
    link = "https://graph.microsoft.com/v1.0/me/calendar/calendarView?$skiptoken=abc"
    page = _response({"value": [], "@odata.nextLink": link})
    client = _client(*[page] * 20)
    connector = MicrosoftGraphCalendarConnector(
        client=client, budget_factory=lambda: _budget(max_pages=20)
    )
    with pytest.raises(CalendarConnectorError, match="wiederholt"):
        await connector.fetch_events(CREDS)


async def test_microsoft_item_and_byte_budget() -> None:
    link = "https://graph.microsoft.com/v1.0/me/calendar/calendarView?$skiptoken={}"
    big = _response({"value": [{"id": "x"}] * 2, "@odata.nextLink": link.format("a")}, size=900)
    big2 = _response({"value": [], "@odata.nextLink": link.format("b")}, size=900)
    connector = MicrosoftGraphCalendarConnector(
        client=_client(big, big2), budget_factory=lambda: _budget()
    )
    with pytest.raises(CalendarConnectorError, match="Datenmenge"):
        await connector.fetch_events(CREDS)


# ── response size is limited while streaming, not after parsing ─────────────────


from app.adapters.calendar.bounded_http import BoundedTransport, make_bounded_client  # noqa: E402


def _bounded(handler, max_bytes: int = 1000) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=BoundedTransport(httpx.MockTransport(handler), max_bytes=max_bytes)
    )


async def test_single_oversized_page_is_aborted_before_it_is_fully_read() -> None:
    delivered = 0

    async def chunks():
        nonlocal delivered
        for _ in range(1000):
            delivered += 100
            yield b"x" * 100

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=chunks(), headers={"content-type": "application/json"})

    async with _bounded(handler, max_bytes=1000) as client:
        with pytest.raises(CalendarConnectorError, match="Datenmenge"):
            await client.get("https://example.test/events")
    assert delivered <= 1200  # stopped near the limit instead of reading 100 kB


async def test_declared_content_length_over_the_limit_is_rejected_up_front() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 10, headers={"content-length": "999999"})

    async with _bounded(handler) as client:
        with pytest.raises(CalendarConnectorError, match="Datenmenge"):
            await client.get("https://example.test/events")


async def test_compressed_responses_are_rejected_to_stop_decompression_bombs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x", headers={"content-encoding": "gzip"})

    async with _bounded(handler) as client:
        with pytest.raises(CalendarConnectorError, match="Komprimierung"):
            await client.get("https://example.test/events")


async def test_identity_encoding_is_requested_and_small_pages_pass() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["accept-encoding"] = request.headers.get("accept-encoding", "")
        return httpx.Response(200, json={"items": []})

    async with _bounded(handler) as client:
        response = await client.get("https://example.test/events")
    assert response.json() == {"items": []}
    assert seen["accept-encoding"] == "identity"


def test_default_client_is_bounded_by_the_configured_limit() -> None:
    client = make_bounded_client()
    assert isinstance(client._transport, BoundedTransport)


async def test_total_deadline_cancels_a_slow_fetch_actively() -> None:
    import asyncio

    async def never_finishes():
        await asyncio.sleep(30)

    with pytest.raises(CalendarConnectorError, match="Zeitbudget"):
        await _budget(max_seconds=0.05).run(never_finishes())


async def test_google_fetch_is_cancelled_when_a_request_hangs() -> None:
    import asyncio

    async def hang(*_, **__):
        await asyncio.sleep(30)

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(side_effect=hang)
    connector = GoogleCalendarConnector(client=client, budget_factory=lambda: _budget(max_seconds=0.05))
    with pytest.raises(CalendarConnectorError, match="Zeitbudget"):
        await connector.fetch_events(CREDS)
