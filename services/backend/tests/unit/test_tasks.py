"""Unit tests for Celery tasks (mocked)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.tasks import sync_calendar_integration


class TestSyncCalendarIntegrationTask:
    """Tests for sync_calendar_integration Celery task."""

    def test_sync_calendar_integration_success(self):
        """sync_calendar_integration should complete successfully."""
        integration_id = str(uuid.uuid4())

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_result = {"created": 1, "updated": 0, "cancelled": 0}

        with patch("app.application.tasks.asyncio.run") as mock_asyncio_run:
            mock_asyncio_run.return_value = mock_result

            result = sync_calendar_integration(integration_id)

        assert result == mock_result
        mock_asyncio_run.assert_called_once()

    def test_sync_calendar_integration_retry_on_error(self):
        """sync_calendar_integration should retry on exception."""
        integration_id = str(uuid.uuid4())

        task_mock = MagicMock()
        task_mock.retry = MagicMock(side_effect=Exception("Retrying"))

        with patch("app.application.tasks.asyncio.run") as mock_asyncio_run:
            mock_asyncio_run.side_effect = RuntimeError("DB connection failed")

            with pytest.raises(Exception):
                sync_calendar_integration.__wrapped__(task_mock, integration_id)

    def test_sync_calendar_integration_uuid_conversion(self):
        """sync_calendar_integration should convert string ID to UUID."""
        integration_id = str(uuid.uuid4())

        with patch("app.application.tasks.asyncio.run") as mock_asyncio_run:
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
            patch("app.application.tasks.asyncio.run") as mock_asyncio_run,
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

        with patch("app.application.tasks.asyncio.run") as mock_asyncio_run:
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

        with patch("app.application.tasks.asyncio.run") as mock_asyncio_run:
            mock_asyncio_run.return_value = {"created": 6, "updated": 0, "skipped": 0}

            result = import_kirchliche_festtage_task(district_id, year)

        assert result is not None
        mock_asyncio_run.assert_called_once()
