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
    """Tests for sync_all_active_integrations Celery task (integration discovery)."""

    def test_sync_all_active_integrations_queues_tasks(self):
        """sync_all_active_integrations should discover and queue sync tasks."""
        # This is more of an integration test, but we can test the basic flow
        from app.application.tasks import sync_all_active_integrations

        fake_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

        with (
            patch(
                "app.application.tasks.asyncio.run", new_callable=CoroutineClosingMock
            ) as mock_asyncio_run,
            patch("app.application.tasks.sync_calendar_integration") as mock_task,
        ):
            mock_asyncio_run.return_value = fake_ids
            mock_task.delay = MagicMock()

            result = sync_all_active_integrations()

        assert result is not None
        assert result["dispatched"] == len(fake_ids)
        mock_asyncio_run.assert_called_once()
        assert mock_task.delay.call_count == len(fake_ids)


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
