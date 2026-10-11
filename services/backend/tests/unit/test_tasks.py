# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Unit tests for Celery tasks (mocked)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.tasks import sync_calendar_integration
from tests.unit.coroutine_mocks import CoroutineClosingMock


class TestSyncCalendarIntegrationTask:
    """Tests for sync_calendar_integration Celery task."""

    def test_sync_calendar_integration_success(self):
        """sync_calendar_integration should complete successfully."""
        integration_id = str(uuid.uuid4())

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_result = {"created": 1, "updated": 0, "cancelled": 0}

        with patch(
            "app.application.tasks.asyncio.run", new_callable=CoroutineClosingMock
        ) as mock_asyncio_run:
            mock_asyncio_run.return_value = mock_result

            result = sync_calendar_integration(integration_id)

        assert result == mock_result
        mock_asyncio_run.assert_called_once()

    def test_sync_calendar_integration_propagates_error_to_autoretry(self):
        """The task body lets errors propagate; Celery's autoretry schedules the retry.

        Backoff behaviour itself is covered in ``test_sync_task_backoff.py``.
        """
        integration_id = str(uuid.uuid4())

        with patch(
            "app.application.tasks.asyncio.run", new_callable=CoroutineClosingMock
        ) as mock_asyncio_run:
            mock_asyncio_run.side_effect = RuntimeError("DB connection failed")

            with pytest.raises(RuntimeError, match="DB connection failed"):
                sync_calendar_integration._orig_run(integration_id)

    def test_sync_calendar_integration_uuid_conversion(self):
        """sync_calendar_integration should convert string ID to UUID."""
        integration_id = str(uuid.uuid4())

        with patch(
            "app.application.tasks.asyncio.run", new_callable=CoroutineClosingMock
        ) as mock_asyncio_run:
            mock_asyncio_run.return_value = {"created": 0, "updated": 0, "cancelled": 0}

            result = sync_calendar_integration(integration_id)

        assert result is not None
        mock_asyncio_run.assert_called_once()


class TestSyncAllActiveIntegrationsTask:
    """Dispatch only due integrations; persist each accepted publish."""

    def _run(self, ids: list[str], *, fail_at: int | None = None) -> tuple:
        from app.application.tasks import sync_all_active_integrations

        session = AsyncMock()
        repo = MagicMock()
        repo.list_active = AsyncMock(return_value=[])
        repo.stamp_scheduled_attempt = AsyncMock()
        engine = MagicMock()
        engine.dispose = AsyncMock()

        with (
            patch("app.adapters.db.session.AsyncSessionLocal") as factory,
            patch("app.adapters.db.session.engine", engine),
            patch(
                "app.adapters.db.repositories.calendar_integration.SqlCalendarIntegrationRepository",
                return_value=repo,
            ),
            patch("app.application.tasks._due_integration_ids", return_value=ids),
            patch("app.application.tasks.sync_calendar_integration") as task,
        ):
            factory.return_value.__aenter__.return_value = session
            if fail_at is not None:
                calls = [None] * fail_at + [ConnectionError("broker unavailable")]
                task.delay.side_effect = calls
                with pytest.raises(ConnectionError, match="broker unavailable"):
                    sync_all_active_integrations()
                result = None
            else:
                result = sync_all_active_integrations()
            assert task.delay.call_count == (fail_at + 1 if fail_at is not None else len(ids))
        return result, repo, session, engine

    def test_sync_all_active_integrations_queues_tasks(self):
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        result, repo, session, engine = self._run(ids)
        assert result == {"dispatched": 2}
        assert repo.stamp_scheduled_attempt.await_count == 2
        assert session.commit.await_count == 2
        engine.dispose.assert_awaited_once()

    def test_failed_broker_publish_does_not_mark_undispatched_integrations(self):
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        _, repo, session, _ = self._run(ids, fail_at=0)
        repo.stamp_scheduled_attempt.assert_not_awaited()
        session.commit.assert_not_awaited()

    def test_prior_successful_publish_remains_stamped_after_later_failure(self):
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        _, repo, session, _ = self._run(ids, fail_at=1)
        repo.stamp_scheduled_attempt.assert_awaited_once()
        assert repo.stamp_scheduled_attempt.await_args.args[0] == uuid.UUID(ids[0])
        session.commit.assert_awaited_once()

    def test_dispatch_timestamp_precedes_published_task_completion(self):
        ids = [str(uuid.uuid4())]
        result, repo, _, _ = self._run(ids)
        assert result == {"dispatched": 1}
        timestamp = repo.stamp_scheduled_attempt.await_args.args[1]
        from datetime import UTC, datetime
        assert timestamp <= datetime.now(UTC)


class TestImportFeiertageTask:
    """Tests for import_feiertage Celery task."""

    def test_import_feiertage_task_success(self):
        """import_feiertage_task should complete successfully."""
        from app.application.tasks import import_feiertage_task

        district_id = str(uuid.uuid4())
        year = 2026

        with patch(
            "app.application.tasks.asyncio.run", new_callable=CoroutineClosingMock
        ) as mock_asyncio_run:
            mock_asyncio_run.return_value = {"created": 10, "updated": 0, "skipped": 5}

            result = import_feiertage_task(district_id, year)

        assert result is not None
        mock_asyncio_run.assert_called_once()


class TestImportKirchlicheFesttageTask:
    """Tests for import_kirchliche_festtage Celery task."""

    def test_import_kirchliche_festtage_task_success(self):
        """import_kirchliche_festtage_task should complete successfully."""
        from app.application.tasks import import_kirchliche_festtage_task

        district_id = str(uuid.uuid4())
        year = 2026

        with patch(
            "app.application.tasks.asyncio.run", new_callable=CoroutineClosingMock
        ) as mock_asyncio_run:
            mock_asyncio_run.return_value = {"created": 6, "updated": 0, "skipped": 0}

            result = import_kirchliche_festtage_task(district_id, year)

        assert result is not None
        mock_asyncio_run.assert_called_once()


class TestGenerateDraftServicesWindowTask:
    """Tests for generate_draft_services_window Celery task."""

    def test_generate_draft_services_window_success(self):
        from app.application.tasks import generate_draft_services_window

        with patch(
            "app.application.tasks.asyncio.run", new_callable=CoroutineClosingMock
        ) as mock_asyncio_run:
            mock_asyncio_run.return_value = {
                "districts": 2,
                "congregations": 9,
                "created": 16,
                "skipped_existing": 30,
                "adopted_existing": 1,
                "invalid_configurations": 0,
            }

            result = generate_draft_services_window()

        assert result["created"] == 16
        assert result["skipped_existing"] == 30
        mock_asyncio_run.assert_called_once()


class TestSyncAllSkipsUnsupportedProviders:
    """#467: automatic sync skips GOOGLE/MICROSOFT integrations with a clear log."""

    def test_due_integration_ids_skips_google_and_microsoft(self, caplog):
        from datetime import UTC, datetime
        from types import SimpleNamespace

        from app.application.tasks import _due_integration_ids
        from app.domain.models.calendar_integration import CalendarType

        def item(cal_type):
            return SimpleNamespace(
                id=uuid.uuid4(), type=cal_type, last_synced_at=None, sync_interval=60
            )

        ics, caldav = item(CalendarType.ICS), item(CalendarType.CALDAV)
        google, microsoft = item(CalendarType.GOOGLE), item(CalendarType.MICROSOFT)

        with caplog.at_level("WARNING", logger="app.application.tasks"):
            ids = _due_integration_ids([ics, google, caldav, microsoft], datetime.now(UTC))

        assert ids == [str(ics.id), str(caldav.id)]
        assert str(google.id) in caplog.text and str(microsoft.id) in caplog.text
        assert "nicht unterstützt" in caplog.text


class TestRunAsSystemWorker:
    """Each Celery task runs on a fresh event loop (``asyncio.run``)."""

    async def test_disposes_engine_pool_before_loop_closes(self):
        """Pooled asyncpg connections must not outlive the loop that opened them."""
        from app.application.tasks import _run_as_system_worker

        async def work():
            return "done"

        engine = MagicMock()
        engine.dispose = AsyncMock()
        with patch("app.adapters.db.session.engine", engine):
            assert await _run_as_system_worker(work()) == "done"

        engine.dispose.assert_awaited_once()

    async def test_disposes_engine_pool_on_failure(self):
        from app.application.tasks import _run_as_system_worker

        async def work():
            raise RuntimeError("boom")

        engine = MagicMock()
        engine.dispose = AsyncMock()
        with (
            patch("app.adapters.db.session.engine", engine),
            pytest.raises(RuntimeError, match="boom"),
        ):
            await _run_as_system_worker(work())

        engine.dispose.assert_awaited_once()


class TestSyncReliability:
    """Retry suppression and independent error persistence (#470)."""

    def test_due_integrations_backoff_blocks_duplicate_retry_chain(self):
        from datetime import UTC, datetime, timedelta
        from types import SimpleNamespace

        from app.application.tasks import _due_integration_ids
        from app.domain.models.calendar_integration import CalendarType

        now = datetime.now(UTC)
        integration = SimpleNamespace(
            id=uuid.uuid4(), type=CalendarType.ICS,
            last_synced_at=now - timedelta(hours=2),
            last_attempt_at=now - timedelta(minutes=10), sync_interval=5,
        )
        assert _due_integration_ids([integration], now) == []
        integration.last_attempt_at = now - timedelta(minutes=31)
        assert _due_integration_ids([integration], now) == [str(integration.id)]

    async def test_record_error_commits_sanitized_text_in_new_session(self):
        from app.application.tasks import record_sync_attempt

        integration = MagicMock(last_attempt_at=None, last_sync_error=None)
        repository = MagicMock()
        repository.get = AsyncMock(return_value=integration)
        repository.save = AsyncMock()
        session = AsyncMock()
        session.commit = AsyncMock()

        with (
            patch(
                "app.adapters.db.session.AsyncSessionLocal",
            ) as session_factory,
            patch(
                "app.adapters.db.repositories.calendar_integration.SqlCalendarIntegrationRepository",
                return_value=repository,
            ),
        ):
            session_factory.return_value.__aenter__.return_value = session
            await record_sync_attempt(uuid.uuid4(), "failure " + "x" * 800)

        assert integration.last_attempt_at is not None
        assert len(integration.last_sync_error) == 500
        repository.save.assert_awaited_once_with(integration)
        session.commit.assert_awaited_once()

    async def test_scheduled_stamp_only_updates_timestamp(self):
        """Scheduler uses the targeted repository update, not aggregate save."""
        from app.application.tasks import mark_scheduled_sync

        session = AsyncMock()
        repository = MagicMock()
        repository.stamp_scheduled_attempt = AsyncMock()
        repository.save = AsyncMock()
        with (
            patch("app.adapters.db.session.AsyncSessionLocal") as session_factory,
            patch(
                "app.adapters.db.repositories.calendar_integration.SqlCalendarIntegrationRepository",
                return_value=repository,
            ),
        ):
            session_factory.return_value.__aenter__.return_value = session
            identifier = uuid.uuid4()
            from datetime import UTC, datetime
            dispatched_at = datetime.now(UTC)
            await mark_scheduled_sync(identifier, dispatched_at)

        repository.stamp_scheduled_attempt.assert_awaited_once()
        assert repository.stamp_scheduled_attempt.await_args.args[0] == identifier
        repository.save.assert_not_awaited()
        session.commit.assert_awaited_once()

    async def test_missing_integration_does_not_create_phantom_status(self):
        from app.application.tasks import record_sync_attempt

        repo = MagicMock()
        repo.get = AsyncMock(return_value=None)
        repo.save = AsyncMock()
        session = AsyncMock()
        with (
            patch("app.adapters.db.session.AsyncSessionLocal") as session_factory,
            patch(
                "app.adapters.db.repositories.calendar_integration.SqlCalendarIntegrationRepository",
                return_value=repo,
            ),
        ):
            session_factory.return_value.__aenter__.return_value = session
            await record_sync_attempt(uuid.uuid4(), "unavailable")

        repo.save.assert_not_awaited()
        session.commit.assert_not_awaited()
