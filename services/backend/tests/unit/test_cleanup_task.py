"""Unit tests for the cleanup_old_events Celery task.

The task deletes PlanningSlot records older than 24 months.
The async DB session is patched so no real database access is performed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.tasks import _delete_expired_drafts, cleanup_old_events
from app.domain.models.planning_slot import ReleasedEventError

# ── helpers ────────────────────────────────────────────────────────────────────


def _make_session_cm(deleted: int = 0) -> tuple[MagicMock, MagicMock]:
    """Return an async context-manager mock that yields a session.

    The session's execute() returns a result with the given rowcount.
    """
    result = MagicMock()
    result.scalars.return_value.all.return_value = [uuid.uuid4() for _ in range(deleted)]

    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, session


# ── tests ─────────────────────────────────────────────────────────────────────


class TestCleanupOldEvents:
    """Tests run the actual task; only the DB layer is replaced with mocks."""

    def _run_task(self, deleted: int = 0):
        """Run cleanup_old_events with a fully mocked DB layer.

        Returns (result, session_mock).
        """
        cm, session = _make_session_cm(deleted)

        with (
            patch("app.adapters.db.session.AsyncSessionLocal", return_value=cm),
            patch("app.adapters.db.repositories.planning_slot.SqlPlanningSlotRepository") as repo_cls,
        ):
            repo_cls.return_value.delete = AsyncMock(return_value=True)
            result = cleanup_old_events()

        return result, session

    def test_returns_deleted_count(self):
        result, _ = self._run_task(deleted=5)
        assert result["deleted"] == 5

    def test_returns_cutoff_in_result(self):
        result, _ = self._run_task()
        assert "cutoff" in result
        cutoff = datetime.fromisoformat(result["cutoff"])
        assert cutoff.tzinfo is not None

    def test_cutoff_is_24_months_in_past(self):
        now = datetime.now(UTC)
        result, _ = self._run_task()
        cutoff = datetime.fromisoformat(result["cutoff"])
        assert cutoff.year == now.year - 2
        assert cutoff.month == now.month

    def test_zero_deletions_when_nothing_to_delete(self):
        result, _ = self._run_task(deleted=0)
        assert result["deleted"] == 0

    def test_calls_execute_with_delete_statement(self):
        _, session = self._run_task(deleted=3)
        # The first statement selects candidates; deletion uses the repository.
        call_arg = session.execute.call_args_list[0][0][0]
        assert "planning_slot" in str(call_arg).lower() or "planningdate" in str(call_arg)
        assert "<" in str(call_arg) or "where" in str(call_arg).lower()

    def test_session_commit_is_called(self):
        _, session = self._run_task(deleted=1)
        session.commit.assert_called_once()

    def test_feb29_leap_year_cutoff_falls_back_to_feb28(self):
        """When today is Feb 29 (leap year), cutoff must be Feb 28 two years back."""
        leap_day = datetime(2024, 2, 29, 12, 0, 0, tzinfo=UTC)

        cm, _session = _make_session_cm(0)

        # Patch datetime.now at module level so the inner _run closure picks it up.
        original_datetime = datetime

        class _FakeDatetime(original_datetime):
            @classmethod
            def now(cls, tz=None):
                return leap_day

        with (
            patch(
                "app.adapters.db.session.AsyncSessionLocal",
                return_value=cm,
            ),
            patch("app.application.tasks.datetime", _FakeDatetime),
            patch("app.adapters.db.repositories.planning_slot.SqlPlanningSlotRepository") as repo_cls,
        ):
            repo_cls.return_value.delete = AsyncMock(return_value=True)
            result = cleanup_old_events()

        cutoff = datetime.fromisoformat(result["cutoff"])
        assert cutoff.year == 2022
        assert cutoff.month == 2
        assert cutoff.day == 28

    def test_bulk_deletion_is_audited_in_the_same_transaction(self):
        _, session = self._run_task(deleted=3)

        assert session.execute.call_count == 2
        statement, rows = session.execute.call_args_list[1][0]
        assert statement.table.name == "audit_logs"
        [row] = rows
        assert row["action"].value == "BULK_OPERATION"
        assert row["resource_type"] == "planning_slot"
        assert row["changes"] == {"operation": "DELETE", "deleted": 3, "reason": "retention"}
        assert row["user_sub"] == "system:celery-worker"
        session.commit.assert_called_once()

    def test_no_audit_entry_when_nothing_was_deleted(self):
        _, session = self._run_task(deleted=0)
        session.execute.assert_called_once()


class TestAggregateRetentionCleanup:
    @pytest.mark.asyncio
    async def test_each_candidate_uses_relationship_safe_repository_delete(self):
        ids = [uuid.uuid4(), uuid.uuid4()]
        result = MagicMock()
        result.scalars.return_value.all.return_value = ids
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        with patch(
            "app.adapters.db.repositories.planning_slot.SqlPlanningSlotRepository"
        ) as repo_cls:
            repo_cls.return_value.delete = AsyncMock(return_value=True)
            count = await _delete_expired_drafts(session, date(2024, 1, 1))
            assert count == 2
            assert [call.args[0] for call in repo_cls.return_value.delete.await_args_list] == ids
        assert session.execute.await_args.args[0].is_select

    @pytest.mark.asyncio
    async def test_skips_candidate_released_or_deleted_during_cleanup(self):

        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        result = MagicMock()
        result.scalars.return_value.all.return_value = ids
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)
        with patch(
            "app.adapters.db.repositories.planning_slot.SqlPlanningSlotRepository"
        ) as repo_cls:
            repo_cls.return_value.delete = AsyncMock(side_effect=[
                True, ReleasedEventError("confirmed"), False,
            ])
            assert await _delete_expired_drafts(session, date(2024, 1, 1)) == 1
            assert repo_cls.return_value.delete.await_count == 3
