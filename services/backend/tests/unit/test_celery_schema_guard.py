# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Celery processes refuse to start against a stale database schema."""

from unittest.mock import AsyncMock, patch

import pytest
from celery import signals

from app import celery_app
from app.adapters.db.schema_version import SchemaVersionError


@pytest.mark.parametrize("signal", [signals.worker_init, signals.beat_init])
def test_worker_and_beat_init_run_schema_guard(signal) -> None:
    receivers = [ref() for _, ref in signal.receivers]
    assert celery_app.assert_schema_current_on_startup in receivers


def test_schema_guard_passes_when_schema_is_current() -> None:
    with (patch.object(celery_app, "assert_database_schema_current", AsyncMock()) as check, patch.object(celery_app, "assert_legacy_broker_drained", AsyncMock())):
        celery_app.assert_schema_current_on_startup()
    check.assert_awaited_once()


def test_schema_guard_exits_on_mismatch() -> None:
    failing = AsyncMock(side_effect=SchemaVersionError("stale"))
    with patch.object(celery_app, "assert_database_schema_current", failing), patch.object(celery_app, "assert_legacy_broker_drained", AsyncMock()):
        with pytest.raises(SystemExit) as excinfo:
            celery_app.assert_schema_current_on_startup()
    assert excinfo.value.code == 1


def test_worker_refuses_to_start_on_unsafe_production_config() -> None:
    """Workers run the same production guard as the API (e.g. owner credentials)."""
    unsafe = patch.object(celery_app, "production_guard", side_effect=RuntimeError("unsafe"))
    with unsafe, patch.object(celery_app, "assert_database_schema_current", AsyncMock()) as check:
        with pytest.raises(SystemExit) as excinfo:
            celery_app.assert_schema_current_on_startup()
    assert excinfo.value.code == 1
    check.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("exists,pending,raises", [
    (False, 0, False),
    (True, 0, False),
    (True, 3, True),
])
async def test_legacy_broker_cutover_guard(exists, pending, raises) -> None:
    """Existing SQL messages block cutover; empty or absent tables do not."""
    from unittest.mock import MagicMock

    db_engine = MagicMock()
    conn = AsyncMock()
    conn.scalar.side_effect = [exists, pending] if exists else [exists]
    db_engine.connect.return_value.__aenter__.return_value = conn
    if raises:
        with pytest.raises(SchemaVersionError, match="queued messages"):
            await celery_app.assert_legacy_broker_drained(db_engine)
    else:
        await celery_app.assert_legacy_broker_drained(db_engine)
    assert conn.scalar.await_count == (2 if exists else 1)
