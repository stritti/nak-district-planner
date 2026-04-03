"""Unit tests for the cleanup_old_events Celery task.

The real task function is executed, but the async DB session factory
(AsyncSessionLocal) and SqlEventRepository are patched so that no real
database or network access is performed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.application.tasks import cleanup_old_events


# ── helpers ────────────────────────────────────────────────────────────────────


def _make_repo_mock(deleted: int = 0) -> MagicMock:
    repo = MagicMock()
    repo.delete_before = AsyncMock(return_value=deleted)
    return repo


def _make_session_cm(repo: MagicMock) -> MagicMock:
    """Return an async context-manager mock that yields a session."""
    session = MagicMock()
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

        Returns (result, repo_mock, session_mock).
        """
        repo = _make_repo_mock(deleted)
        cm, session = _make_session_cm(repo)

        with (
            patch(
                "app.adapters.db.session.AsyncSessionLocal",
                return_value=cm,
            ),
            patch(
                "app.adapters.db.repositories.event.SqlEventRepository",
                return_value=repo,
            ),
        ):
            result = cleanup_old_events()

        return result, repo, session

    def test_returns_deleted_count(self):
        result, _, _ = self._run_task(deleted=5)
        assert result["deleted"] == 5

    def test_returns_cutoff_in_result(self):
        result, _, _ = self._run_task()
        assert "cutoff" in result
        cutoff = datetime.fromisoformat(result["cutoff"])
        assert cutoff.tzinfo is not None

    def test_cutoff_is_24_months_in_past(self):
        now = datetime.now(timezone.utc)
        result, _, _ = self._run_task()
        cutoff = datetime.fromisoformat(result["cutoff"])
        assert cutoff.year == now.year - 2
        assert cutoff.month == now.month

    def test_zero_deletions_when_nothing_to_delete(self):
        result, _, _ = self._run_task(deleted=0)
        assert result["deleted"] == 0

    def test_delete_before_receives_timezone_aware_cutoff(self):
        _, repo, _ = self._run_task(deleted=3)
        repo.delete_before.assert_called_once()
        cutoff_arg = repo.delete_before.call_args[0][0]
        assert isinstance(cutoff_arg, datetime)
        assert cutoff_arg.tzinfo is not None

    def test_session_commit_is_called(self):
        _, _, session = self._run_task(deleted=1)
        session.commit.assert_called_once()

    def test_feb29_leap_year_cutoff_falls_back_to_feb28(self):
        """When today is Feb 29 (leap year), cutoff must be Feb 28 two years back."""
        leap_day = datetime(2024, 2, 29, 12, 0, 0, tzinfo=timezone.utc)

        repo = _make_repo_mock(0)
        cm, session = _make_session_cm(repo)

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
            patch(
                "app.adapters.db.repositories.event.SqlEventRepository",
                return_value=repo,
            ),
            patch("app.application.tasks.datetime", _FakeDatetime),
        ):
            result = cleanup_old_events()

        cutoff = datetime.fromisoformat(result["cutoff"])
        assert cutoff.year == 2022
        assert cutoff.month == 2
        assert cutoff.day == 28
