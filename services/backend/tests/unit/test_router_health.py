from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from starlette.requests import Request

from app.adapters.api.routers.health import health


def _request(path: str) -> Request:
    return Request({"type": "http", "path": path, "headers": [], "query_string": b""})


class _SessionContext:
    def __init__(self, session: AsyncMock) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncMock:
        return self.session

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None


@pytest.mark.asyncio
async def test_health_returns_ok_when_database_and_redis_are_available() -> None:
    session = AsyncMock()
    redis_client = AsyncMock()

    with (
        patch("app.adapters.api.routers.health.AsyncSessionLocal", return_value=_SessionContext(session)),
        patch("app.adapters.api.routers.health.rate_limiter._redis", redis_client),
    ):
        response = await health(_request("/health"))

    payload = json.loads(response.body)
    assert response.status_code == status.HTTP_200_OK
    assert payload["status"] == "ok"
    assert payload["db"] == "ok"
    assert payload["redis"] == "ok"
    assert "version" in payload


@pytest.mark.asyncio
async def test_health_returns_503_when_database_is_unavailable() -> None:
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("database unavailable")
    redis_client = AsyncMock()

    with (
        patch("app.adapters.api.routers.health.AsyncSessionLocal", return_value=_SessionContext(session)),
        patch("app.adapters.api.routers.health.rate_limiter._redis", redis_client),
    ):
        response = await health(_request("/health"))

    payload = json.loads(response.body)
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert payload["status"] == "degraded"
    assert payload["db"] == "error"
    assert payload["redis"] == "ok"


@pytest.mark.asyncio
async def test_health_returns_503_when_redis_is_unavailable() -> None:
    session = AsyncMock()
    redis_client = AsyncMock()
    redis_client.ping.side_effect = RuntimeError("redis unavailable")

    with (
        patch("app.adapters.api.routers.health.AsyncSessionLocal", return_value=_SessionContext(session)),
        patch("app.adapters.api.routers.health.rate_limiter._redis", redis_client),
    ):
        response = await health(_request("/health"))

    payload = json.loads(response.body)
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert payload["status"] == "degraded"
    assert payload["db"] == "ok"
    assert payload["redis"] == "error"
    session.execute.assert_awaited_once()
    redis_client.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_legacy_health_preserves_redis_ping_failure_status() -> None:
    session = AsyncMock()
    redis_client = AsyncMock()
    redis_client.ping.side_effect = RuntimeError("redis unavailable")

    with (
        patch("app.adapters.api.routers.health.AsyncSessionLocal", return_value=_SessionContext(session)),
        patch("app.adapters.api.routers.health.rate_limiter._redis", redis_client),
    ):
        response = await health(_request("/api/health"))

    payload = json.loads(response.body)
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert payload["redis"] == "unavailable"
    assert "db" not in payload


@pytest.mark.asyncio
async def test_legacy_health_reports_disconnected_when_redis_is_not_connected() -> None:
    session = AsyncMock()

    with (
        patch("app.adapters.api.routers.health.AsyncSessionLocal", return_value=_SessionContext(session)),
        patch("app.adapters.api.routers.health.rate_limiter._redis", None),
    ):
        response = await health(_request("/api/health"))

    payload = json.loads(response.body)
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert payload["redis"] == "disconnected"
