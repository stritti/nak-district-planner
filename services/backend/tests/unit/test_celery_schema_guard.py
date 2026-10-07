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
    with patch.object(celery_app, "assert_database_schema_current", AsyncMock()) as check:
        celery_app.assert_schema_current_on_startup()
    check.assert_awaited_once()


def test_schema_guard_exits_on_mismatch() -> None:
    failing = AsyncMock(side_effect=SchemaVersionError("stale"))
    with patch.object(celery_app, "assert_database_schema_current", failing):
        with pytest.raises(SystemExit) as excinfo:
            celery_app.assert_schema_current_on_startup()
    assert excinfo.value.code == 1
