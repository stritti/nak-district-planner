from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import main


def test_configure_logging_runs() -> None:
    main.configure_logging()


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    out = await main.health()
    if hasattr(out, "status_code"):
        assert out.status_code in (200, 503)
    else:
        assert out["status"] == "ok"
        assert out["version"] == main.settings.app_version
        assert "database" in out


@pytest.mark.asyncio
async def test_health_endpoint_degrades_when_redis_disconnected() -> None:
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    with patch("app.main.AsyncSessionLocal", return_value=mock_session):
        from app.application.rate_limiter import rate_limiter

        previous_redis = rate_limiter._redis
        rate_limiter._redis = None
        try:
            out = await main.health()
        finally:
            rate_limiter._redis = previous_redis

    assert hasattr(out, "status_code"), "expected health() to return a response when degraded"
    assert out.status_code == 503
    assert b'"status":"degraded"' in out.body
    assert b'"redis":"disconnected"' in out.body


@pytest.mark.asyncio
async def test_unhandled_exception_handler() -> None:
    with patch("app.main.traceback.print_exc"), patch("app.main.sys.stderr.flush"):
        response = await main._unhandled(MagicMock(), RuntimeError("boom"))
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_lifespan_initializes_and_cleans_up() -> None:
    with (
        patch("asyncio.to_thread", new=AsyncMock()),
        patch("app.main.httpx.AsyncClient") as client_cls,
        patch("app.main.OIDCAdapter") as adapter_cls,
        patch("app.main.deps.set_oidc_adapter"),
        patch.object(main.settings, "startup_generate_draft_services", False),
    ):
        client_cls.return_value = MagicMock()
        adapter = AsyncMock()
        adapter.discover = AsyncMock()
        adapter.close = AsyncMock()
        adapter.issuer = "https://issuer"
        adapter_cls.return_value = adapter

        async with main.lifespan(main.app):
            pass

        adapter.discover.assert_awaited_once()
        adapter.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_startup_redis_failure_does_not_increment_fail_open_counter() -> None:
    with (
        patch("asyncio.to_thread", new=AsyncMock()),
        patch("app.main.httpx.AsyncClient") as client_cls,
        patch("app.main.OIDCAdapter") as adapter_cls,
        patch("app.main.deps.set_oidc_adapter"),
        patch.object(main.settings, "startup_generate_draft_services", False),
        patch("app.main.rate_limiter.connect", new=AsyncMock(side_effect=Exception("Redis down"))),
        patch("app.application.rate_limiter.increment_fail_open_counter") as increment_mock,
    ):
        client_cls.return_value = MagicMock()
        adapter = AsyncMock()
        adapter.discover = AsyncMock()
        adapter.close = AsyncMock()
        adapter.issuer = "https://issuer"
        adapter_cls.return_value = adapter

        async with main.lifespan(main.app):
            pass

    increment_mock.assert_not_called()
