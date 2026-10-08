"""Exponential backoff, structured failure logs and alerting of the sync task."""

from __future__ import annotations

import logging
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry
from celery.utils.time import get_exponential_backoff_interval

from app.application import tasks
from app.application.tasks import (
    SYNC_MAX_RETRIES,
    SYNC_RETRY_BACKOFF_MAX_SECONDS,
    SYNC_RETRY_BACKOFF_SECONDS,
    sync_calendar_integration,
)
from app.domain.errors import IntegrationNotFoundError
from tests.unit.coroutine_mocks import close_coroutine


@pytest.fixture
def integration_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def request_context():
    """Simulate the Celery request of the n-th delivery of the task."""
    pushed = 0

    def push(retries: int) -> None:
        nonlocal pushed
        sync_calendar_integration.push_request(retries=retries)
        pushed += 1

    yield push
    for _ in range(pushed):
        sync_calendar_integration.pop_request()


def _close_coroutine_and_raise(exc: BaseException):
    def run(coro):
        close_coroutine(coro)
        raise exc

    return run


class TestRetryConfiguration:
    def test_task_uses_exponential_backoff_with_jitter(self) -> None:
        assert sync_calendar_integration.max_retries == SYNC_MAX_RETRIES
        assert sync_calendar_integration.retry_backoff == SYNC_RETRY_BACKOFF_SECONDS
        assert sync_calendar_integration.retry_backoff_max == SYNC_RETRY_BACKOFF_MAX_SECONDS
        assert sync_calendar_integration.retry_jitter is True
        assert IntegrationNotFoundError in sync_calendar_integration.dont_autoretry_for

    def test_backoff_schedule_doubles_until_cap(self) -> None:
        delays = [
            get_exponential_backoff_interval(
                factor=SYNC_RETRY_BACKOFF_SECONDS,
                retries=retries,
                maximum=SYNC_RETRY_BACKOFF_MAX_SECONDS,
                full_jitter=False,
            )
            for retries in range(8)
        ]
        assert delays == [60, 120, 240, 480, 960, 1920, 3600, 3600]


class TestRetryBehaviour:
    @pytest.mark.parametrize("retries", [0, 1, 3])
    def test_transient_failure_is_retried_within_exponential_bound(
        self, integration_id, request_context, retries
    ) -> None:
        request_context(retries)
        with (
            patch.object(tasks.asyncio, "run", side_effect=_close_coroutine_and_raise(OSError())),
            patch.object(sync_calendar_integration, "retry", return_value=Retry()) as retry,
            pytest.raises(Retry),
        ):
            sync_calendar_integration.run(integration_id)

        retry.assert_called_once()
        countdown = retry.call_args.kwargs["countdown"]
        assert 0 <= countdown <= SYNC_RETRY_BACKOFF_SECONDS * 2**retries
        assert isinstance(retry.call_args.kwargs["exc"], OSError)

    def test_missing_integration_is_not_retried(self, integration_id, request_context) -> None:
        request_context(0)
        error = IntegrationNotFoundError("gone")
        with (
            patch.object(tasks.asyncio, "run", side_effect=_close_coroutine_and_raise(error)),
            patch.object(sync_calendar_integration, "retry") as retry,
            pytest.raises(IntegrationNotFoundError),
        ):
            sync_calendar_integration.run(integration_id)

        retry.assert_not_called()

    def test_success_returns_summary_without_retry(self, integration_id, request_context) -> None:
        request_context(0)
        summary = {"created": 1, "updated": 0, "cancelled": 0}

        def run(coro):
            close_coroutine(coro)
            return summary

        with (
            patch.object(tasks.asyncio, "run", side_effect=run),
            patch.object(sync_calendar_integration, "retry") as retry,
        ):
            assert sync_calendar_integration.run(integration_id) == summary

        retry.assert_not_called()


class TestFailureHooks:
    def test_on_retry_logs_structured_context_without_exception_text(
        self, integration_id, request_context, caplog
    ) -> None:
        request_context(1)
        exc = RuntimeError("secret://token@provider")

        with caplog.at_level(logging.WARNING, logger=tasks.logger.name):
            sync_calendar_integration.on_retry(exc, "task-id", (integration_id,), {}, None)

        record = caplog.records[-1]
        assert record.integration_id == integration_id
        assert record.error_class == "RuntimeError"
        assert record.attempt == 2
        assert "secret://" not in caplog.text

    def test_on_failure_logs_and_alerts_once_retries_are_exhausted(
        self, integration_id, request_context, caplog
    ) -> None:
        request_context(SYNC_MAX_RETRIES)
        exc = TimeoutError()

        with (
            patch.object(tasks, "_alert_sync_failure", new=AsyncMock()) as alert,
            caplog.at_level(logging.ERROR, logger=tasks.logger.name),
        ):
            sync_calendar_integration.on_failure(
                exc, "task-id", (), {"integration_id": integration_id}, None
            )

        alert.assert_awaited_once_with(integration_id, exc, SYNC_MAX_RETRIES + 1)
        assert caplog.records[-1].error_class == "TimeoutError"

    def test_on_failure_without_integration_id_only_logs(self, request_context) -> None:
        request_context(0)
        with patch.object(tasks, "_alert_sync_failure", new=AsyncMock()) as alert:
            sync_calendar_integration.on_failure(RuntimeError(), "task-id", (), {}, None)

        alert.assert_not_awaited()

    def test_alert_failure_never_masks_original_error(
        self, integration_id, request_context, caplog
    ) -> None:
        request_context(SYNC_MAX_RETRIES)
        with (
            patch.object(
                tasks, "_alert_sync_failure", new=AsyncMock(side_effect=OSError("db down"))
            ),
            caplog.at_level(logging.ERROR, logger=tasks.logger.name),
        ):
            sync_calendar_integration.on_failure(
                RuntimeError(), "task-id", (integration_id,), {}, None
            )

        assert "alert could not be created" in caplog.text


class TestAlertWiring:
    async def test_alert_commits_only_when_notification_was_created(self, integration_id) -> None:
        session = MagicMock()
        session.commit = AsyncMock()
        session_factory = MagicMock()
        session_factory.return_value.__aenter__ = AsyncMock(return_value=session)
        session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.adapters.db.session.AsyncSessionLocal", session_factory),
            patch(
                "app.application.sync_failure_alerts.SyncFailureAlerter.alert",
                new=AsyncMock(side_effect=[object(), None]),
            ) as alert,
        ):
            await tasks._alert_sync_failure(integration_id, TimeoutError(), 5)
            await tasks._alert_sync_failure(integration_id, TimeoutError(), 5)

        failure = alert.await_args_list[0].args[0]
        assert failure.integration_id == uuid.UUID(integration_id)
        assert failure.error_class == "TimeoutError"
        assert failure.attempts == 5
        session.commit.assert_awaited_once()
