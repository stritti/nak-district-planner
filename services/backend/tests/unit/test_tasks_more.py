"""Unit tests for additional Celery tasks (mocked).

All internal imports in the task functions (asyncio.run, from X import Y)
must be patched at their defining module, not at the tasks module namespace.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.application.tasks import (
    auto_import_feiertage,
    check_version,
    cleanup_old_events,
    trigger_docker_update,
)


class TestCleanupOldEvents:
    """Tests for cleanup_old_events Celery task."""

    def test_cleanup_old_events_success(self):
        with patch("app.application.tasks.asyncio.run") as mock_run:
            mock_run.return_value = {"deleted": 5, "cutoff": "2024-06-15T00:00:00+00:00"}

            result = cleanup_old_events()

            assert result["deleted"] == 5
            mock_run.assert_called_once()

    def test_cleanup_old_events_feb29_edge_case(self):
        """Test that Feb-29 edge case doesn't crash."""
        with patch("app.application.tasks.asyncio.run") as mock_run:
            mock_run.return_value = {"deleted": 0, "cutoff": "2024-02-29T00:00:00+00:00"}

            result = cleanup_old_events()

            assert result["deleted"] == 0
            mock_run.assert_called_once()


class TestCheckVersionTask:
    """Tests for check_version Celery task."""

    def test_check_version_success(self):
        mock_cache = MagicMock()
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_latest_version.return_value = "v0.9.0"

        # These imports are INSIDE the check_version function body, so we must
        # patch at the defining module, not at app.application.tasks.
        with (
            patch("app.adapters.version_check.cache.version_cache", mock_cache),
            patch("app.adapters.version_check.ghcr.GhcrTagFetcher", return_value=mock_fetcher) as _,
            patch("app.config.settings") as mock_settings,
        ):
            mock_settings.app_version = "v0.8.0"
            result = check_version()

            assert result["latest"] == "v0.9.0"
            mock_fetcher.fetch_latest_version.assert_called_once_with("backend")
            mock_cache.set.assert_called_once_with("v0.9.0")


class TestTriggerDockerUpdate:
    """Tests for trigger_docker_update Celery task."""

    def test_no_compose_dir_returns_error(self):
        with patch("app.config.settings") as mock_settings:
            mock_settings.docker_compose_dir = ""

            result = trigger_docker_update()

            assert result["status"] == "error"
            assert "not configured" in result["message"]

    def test_success_path(self):
        with (
            patch("app.config.settings") as mock_settings,
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_settings.docker_compose_dir = "/app"
            mock_run.return_value = MagicMock(returncode=0, stderr="")

            result = trigger_docker_update()

            assert result["status"] == "ok"
            assert mock_run.call_count == 2  # pull + up

    def test_pull_failure(self):
        with (
            patch("app.config.settings") as mock_settings,
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_settings.docker_compose_dir = "/app"
            mock_run.return_value = MagicMock(returncode=1, stderr="pull failed")

            result = trigger_docker_update()

            assert result["status"] == "error"
            assert "failed" in str(result["details"])

    def test_pull_timeout(self):
        with (
            patch("app.config.settings") as mock_settings,
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_settings.docker_compose_dir = "/app"
            mock_run.side_effect = TimeoutError("timeout")

            result = trigger_docker_update()

            assert result["status"] == "error"

    def test_directory_not_found(self):
        with patch("app.config.settings") as mock_settings:
            mock_settings.docker_compose_dir = "/nonexistent"
            with patch("pathlib.Path.exists", return_value=False):
                result = trigger_docker_update()

                assert result["status"] == "error"
                assert "not found" in result["message"]


class TestAutoImportFeiertage:
    """Tests for auto_import_feiertage Celery task."""

    def test_auto_import_success(self):
        with patch("app.application.tasks.asyncio.run") as mock_run:
            mock_run.return_value = {
                "years": [2026],
                "districts": 2,
                "created": 24,
                "updated": 0,
                "skipped": 0,
            }

            result = auto_import_feiertage()

            assert result["years"] == [2026]
            assert result["created"] == 24
            mock_run.assert_called_once()
