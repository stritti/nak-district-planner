"""Unit tests for fail-fast database schema version verification."""

import socket
from contextlib import AbstractAsyncContextManager
from typing import Any

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.db import schema_version


class _ScriptDirectory:
    def __init__(self, heads: list[str]):
        self._heads = heads

    def get_heads(self) -> list[str]:
        return self._heads


class _Connection:
    def __init__(self, rows: list[tuple[str]] | None = None, error: Exception | None = None):
        self._rows = rows or []
        self._error = error

    async def execute(self, _statement: Any) -> list[tuple[str]]:
        if self._error is not None:
            raise self._error
        return self._rows


class _ConnectionContext(AbstractAsyncContextManager[_Connection]):
    def __init__(self, connection: _Connection):
        self._connection = connection

    async def __aenter__(self) -> _Connection:
        return self._connection

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class _Engine:
    def __init__(self, connection: _Connection):
        self._connection = connection

    def connect(self) -> _ConnectionContext:
        return _ConnectionContext(self._connection)


def _set_expected_heads(monkeypatch: pytest.MonkeyPatch, heads: list[str]) -> None:
    monkeypatch.setattr(
        schema_version.ScriptDirectory,
        "from_config",
        lambda _config: _ScriptDirectory(heads),
    )


def test_expected_schema_revisions_rejects_missing_head(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_expected_heads(monkeypatch, [])

    with pytest.raises(schema_version.SchemaVersionError, match="no configured head"):
        schema_version.expected_schema_revisions()


@pytest.mark.asyncio
async def test_schema_assert_accepts_database_at_expected_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_expected_heads(monkeypatch, ["0021"])
    engine = _Engine(_Connection(rows=[("0021",)]))

    await schema_version.assert_database_schema_current(engine)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_schema_assert_rejects_stale_database(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_expected_heads(monkeypatch, ["0021"])
    engine = _Engine(_Connection(rows=[("0020",)]))

    with pytest.raises(schema_version.SchemaVersionError, match="revision mismatch"):
        await schema_version.assert_database_schema_current(engine)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_schema_assert_rejects_unreadable_version_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_expected_heads(monkeypatch, ["0021"])
    engine = _Engine(_Connection(error=SQLAlchemyError("missing table")))

    with pytest.raises(schema_version.SchemaVersionError, match="Could not read"):
        await schema_version.assert_database_schema_current(engine)  # type: ignore[arg-type]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [ConnectionRefusedError("refused"), socket.gaierror("no such host"), TimeoutError()],
)
async def test_schema_assert_rejects_unreachable_database(
    monkeypatch: pytest.MonkeyPatch, error: OSError
) -> None:
    """Driver-level connection errors must stop the worker, not slip past the guard."""
    _set_expected_heads(monkeypatch, ["0021"])
    engine = _Engine(_Connection(error=error))

    with pytest.raises(schema_version.SchemaVersionError, match="Could not read"):
        await schema_version.assert_database_schema_current(engine)  # type: ignore[arg-type]
