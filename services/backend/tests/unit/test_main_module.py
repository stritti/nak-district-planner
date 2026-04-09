from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import main


def test_configure_logging_runs() -> None:
    main.configure_logging()


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    out = await main.health()
    assert out == {"status": "ok"}


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
