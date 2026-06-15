"""Tests for app/adapters/db/session.py — get_db_session generator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.db.session import get_db_session


@pytest.mark.asyncio
async def test_get_db_session_success():
    """get_db_session should yield a session and commit on success."""
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    with patch("app.adapters.db.session.AsyncSessionLocal", return_value=mock_session):
        gen = get_db_session()
        session = await gen.__anext__()

        assert session is mock_session
        mock_session.commit.assert_not_called()

        # Finish the generator — should trigger commit
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()

        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_db_session_rollback_on_error():
    """get_db_session should rollback when context raises."""
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    with patch("app.adapters.db.session.AsyncSessionLocal", return_value=mock_session):
        gen = get_db_session()
        session = await gen.__anext__()
        assert session is mock_session

        # Throw an exception into the generator
        with pytest.raises(RuntimeError):
            await gen.athrow(RuntimeError("test error"))

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_db_session_close_on_exit():
    """get_db_session should close session when generator is closed."""
    mock_session = MagicMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("app.adapters.db.session.AsyncSessionLocal", return_value=mock_session):
        gen = get_db_session()
        session = await gen.__anext__()
        assert session is mock_session

        await gen.aclose()
