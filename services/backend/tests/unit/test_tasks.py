# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Unit tests for Celery tasks (mocked)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.worker.tasks import sync_calendar_integration
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
            "app.adapters.worker.tasks.asyncio.run", new_callable=CoroutineClosingMock
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
            "app.adapters.worker.tasks.asyncio.run", new_callable=CoroutineClosingMock
        ) as mock_asyncio_run:
            mock_asyncio_run.side_effect = RuntimeError("DB connection failed")

            with pytest.raises(RuntimeError, match="DB connection failed"):
                sync_calendar_integration._orig_run(integration_id)

    def test_sync_calendar_integration_uuid_conversion(self):
        """sync_calendar_integration should convert string ID to UUID."""
        integration_id = str(uuid.uuid4())

        with patch(
            "app.adapters.worker.tasks.asyncio.run", new_callable=CoroutineClosingMock
        ) as mock_asyncio_run:
            mock_asyncio_run.return_value = {"created": 0, "updated": 0, "cancelled": 0}

            result = sync_calendar_integration(integration_id)

        assert result is not None
        mock_asyncio_run.assert_called_once()


class TestSyncAllActiveIntegrationsTask:
    """Dispatch only due integrations; persist each accepted publish."""

    def _run(self, ids: list[str], *, fail_at: int | None = None) -> tuple:
        from app.adapters.worker.tasks import sync_all_active_integrations

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
            patch("app.adapters.worker.tasks._due_integration_ids", return_value=ids),
            patch("app.adapters.worker.tasks.sync_calendar_integration") as task,
        ):
            factory.return_value.__aenter__.return_value = session
            if fail_at is not None:
                calls = [None] * fail_at + [ConnectionError("broker unavailable")] + [None] * (
                    len(ids) - fail_at - 1
                )
                task.delay.side_effect = calls
                result = sync_all_active_integrations()
            else:
                result = sync_all_active_integrations()
            assert task.delay.call_count == len(ids)
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
        result, repo, session, _ = self._run(ids, fail_at=0)
        assert result == {"dispatched": 1}
        repo.stamp_scheduled_attempt.assert_awaited_once()
        assert repo.stamp_scheduled_attempt.await_args.args[0] == uuid.UUID(ids[1])
        assert session.commit.await_count == 1
        assert session.rollback.await_count == 1

    def test_prior_successful_publish_remains_stamped_after_later_failure(self):
        ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        result, repo, session, _ = self._run(ids, fail_at=1)
        assert result == {"dispatched": 1}
        repo.stamp_scheduled_attempt.assert_awaited_once()
        assert repo.stamp_scheduled_attempt.await_args.args[0] == uuid.UUID(ids[0])
        assert session.commit.await_count == 1
        assert session.rollback.await_count == 1

    def test_dispatch_timestamp_precedes_published_task_completion(self):
        ids = [str(uuid.uuid4())]
        result, repo, _, _ = self._run(ids)
        assert result == {"dispatched": 1}
        timestamp = repo.stamp_scheduled_attempt.await_args.args[1]
        from datetime import UTC, datetime
        assert timestamp <= datetime.now(UTC)



class TestGenerateDraftServicesWindowTask:
    """Tests for generate_draft_services_window Celery task."""

    def test_generate_draft_services_window_success(self):
        from app.adapters.worker.tasks import generate_draft_services_window

        with patch(
            "app.adapters.worker.tasks.asyncio.run", new_callable=CoroutineClosingMock
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

        from app.adapters.worker.tasks import _due_integration_ids
        from app.domain.models.calendar_integration import CalendarType

        def item(cal_type):
            return SimpleNamespace(
                id=uuid.uuid4(), type=cal_type, last_synced_at=None, sync_interval=60
            )

        ics, caldav = item(CalendarType.ICS), item(CalendarType.CALDAV)
        google, microsoft = item(CalendarType.GOOGLE), item(CalendarType.MICROSOFT)

        with caplog.at_level("WARNING", logger="app.adapters.worker.tasks"):
            ids = _due_integration_ids([ics, google, caldav, microsoft], datetime.now(UTC))

        assert ids == [str(ics.id), str(caldav.id)]
        assert str(google.id) in caplog.text and str(microsoft.id) in caplog.text
        assert "nicht unterstützt" in caplog.text


class TestRunAsSystemWorker:
    """Each Celery task runs on a fresh event loop (``asyncio.run``)."""

    async def test_disposes_engine_pool_before_loop_closes(self):
        """Pooled asyncpg connections must not outlive the loop that opened them."""
        from app.adapters.worker.tasks import _run_as_system_worker

        async def work():
            return "done"

        engine = MagicMock()
        engine.dispose = AsyncMock()
        with patch("app.adapters.db.session.engine", engine):
            assert await _run_as_system_worker(work()) == "done"

        engine.dispose.assert_awaited_once()

    async def test_disposes_engine_pool_on_failure(self):
        from app.adapters.worker.tasks import _run_as_system_worker

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

        from app.adapters.worker.tasks import _due_integration_ids
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
        from app.adapters.worker.tasks import record_sync_attempt

        repo = MagicMock()
        repo.record_attempt = AsyncMock()
        session = AsyncMock()
        session.commit = AsyncMock()

        with (
            patch("app.adapters.db.session.AsyncSessionLocal") as session_factory,
            patch(
                "app.adapters.db.repositories.calendar_integration.SqlCalendarIntegrationRepository",
                return_value=repo,
            ),
        ):
            session_factory.return_value.__aenter__.return_value = session
            await record_sync_attempt(uuid.uuid4(), "failure " + "x" * 800)

        assert repo.record_attempt.await_count == 1
        args = repo.record_attempt.await_args.args
        assert args[2] == "failure " + "x" * 800
        repo.record_attempt.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_record_attempt_truncates_error_text(self):
        from datetime import UTC, datetime

        from app.adapters.db.repositories.calendar_integration import (
            SqlCalendarIntegrationRepository,
        )

        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
        repo = SqlCalendarIntegrationRepository(session)
        integration_id = uuid.uuid4()
        at = datetime.now(UTC)
        long_error = "x" * 800

        await repo.record_attempt(integration_id, at, long_error)

        statement = session.execute.await_args.args[0]
        compiled = statement.compile(compile_kwargs={"literal_binds": False})
        assert "last_attempt_at" in str(compiled)
        assert "last_sync_error" in str(compiled)
        error_params = [
            value for value in compiled.params.values() if isinstance(value, str)
        ]
        assert error_params and len(error_params[0]) == 500

    async def test_record_attempt_targeted_update_only(self):
        from datetime import UTC, datetime

        from app.adapters.db.repositories.calendar_integration import (
            SqlCalendarIntegrationRepository,
        )

        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
        repo = SqlCalendarIntegrationRepository(session)
        integration_id = uuid.uuid4()
        at = datetime.now(UTC)

        await repo.record_attempt(integration_id, at, "Synchronisierung fehlgeschlagen (X)")

        statement = session.execute.await_args.args[0]
        compiled = str(statement.compile())
        for column in (
            "last_synced_at",
            "updated_at",
            "is_active",
            "sync_interval",
            "name",
            "credentials_enc",
        ):
            assert column not in compiled, f"targeted update must not touch {column}"

    async def test_record_attempt_returns_row_updated_flag(self):
        from datetime import UTC, datetime

        from app.adapters.db.repositories.calendar_integration import (
            SqlCalendarIntegrationRepository,
        )

        session = MagicMock()
        result = MagicMock(rowcount=1)
        session.execute = AsyncMock(return_value=result)
        repo = SqlCalendarIntegrationRepository(session)

        assert await repo.record_attempt(uuid.uuid4(), datetime.now(UTC), None) is True

        result.rowcount = 0
        assert await repo.record_attempt(uuid.uuid4(), datetime.now(UTC), None) is False

    async def test_missing_integration_does_not_create_phantom_status(self):
        from app.adapters.worker.tasks import record_sync_attempt

        repo = MagicMock()
        repo.record_attempt = AsyncMock()
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

        repo.record_attempt.assert_awaited_once()
        session.commit.assert_awaited_once()

def test_draft_worker_supplies_required_district_and_congregation_repositories() -> None:
    """Run the real task coroutine and verify all required constructor ports."""
    from app.adapters.worker.tasks import generate_draft_services_window

    session = AsyncMock()
    summary = {
        "districts": 1, "congregations": 2, "created": 3,
        "skipped_existing": 0, "adopted_existing": 0,
        "invalid_configurations": 0,
    }

    with (
        patch("app.adapters.db.session.AsyncSessionLocal") as session_factory,
        patch("app.adapters.db.repositories.district.SqlDistrictRepository") as district_repo,
        patch(
            "app.adapters.db.repositories.congregation.SqlCongregationRepository"
        ) as congregation_repo,
        patch("app.adapters.db.repositories.planning_slot.SqlPlanningSlotRepository"),
        patch("app.adapters.db.repositories.event_instance.SqlEventInstanceRepository"),
        patch(
            "app.application.draft_service_generation.GenerateDraftServicesUseCase"
        ) as use_case,
        patch("app.adapters.worker.tasks._run_as_system_worker", side_effect=lambda work: work),
    ):
        session_factory.return_value.__aenter__.return_value = session
        use_case.return_value.run = AsyncMock(return_value=summary)
        result = generate_draft_services_window()

    assert result == summary
    kwargs = use_case.call_args.kwargs
    assert kwargs["district_repo"] is district_repo.return_value
    assert kwargs["congregation_repo"] is congregation_repo.return_value
    session.commit.assert_awaited_once()
