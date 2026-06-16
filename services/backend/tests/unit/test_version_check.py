"""Unit tests for version check and self-update functionality."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from app.adapters.version_check.cache import VersionCache
from app.adapters.version_check.ghcr import SemVer, latest_semver, parse_semver_tags


class TestSemVer:
    """Tests for SemVer value object."""

    def test_parse_valid_semver(self):
        v = SemVer.parse("0.4.5")
        assert v is not None
        assert v.major == 0
        assert v.minor == 4
        assert v.patch == 5

    def test_parse_with_v_prefix(self):
        v = SemVer.parse("v0.4.5")
        assert v is not None
        assert v.major == 0
        assert v.minor == 4
        assert v.patch == 5

    def test_parse_invalid(self):
        assert SemVer.parse("latest") is None
        assert SemVer.parse("0.4") is None
        assert SemVer.parse("abc") is None
        assert SemVer.parse("0.4.5.6") is None

    def test_ordering(self):
        v1 = SemVer(0, 4, 5)
        v2 = SemVer(0, 5, 0)
        v3 = SemVer(1, 0, 0)
        assert v1 < v2
        assert v2 < v3
        assert sorted([v3, v1, v2]) == [v1, v2, v3]

    def test_str(self):
        assert str(SemVer(0, 4, 5)) == "0.4.5"


class TestParseSemverTags:
    """Tests for parse_semver_tags utility."""

    def test_all_valid(self):
        tags = ["0.4.5", "0.5.0", "v1.0.0"]
        result = parse_semver_tags(tags)
        assert len(result) == 3

    def test_mixed_with_invalid(self):
        tags = ["0.4.5", "latest", "v0.5.0", "sha-abc123", "0.4"]
        result = parse_semver_tags(tags)
        assert len(result) == 2

    def test_empty(self):
        assert parse_semver_tags([]) == []


class TestLatestSemver:
    """Tests for latest_semver function."""

    def test_highest_version(self):
        tags = ["0.4.5", "0.5.0", "0.3.0", "v1.0.0"]
        assert latest_semver(tags) == "1.0.0"

    def test_with_latest_tag(self):
        tags = ["0.4.5", "0.5.0", "latest"]
        assert latest_semver(tags) == "0.5.0"

    def test_no_valid_versions(self):
        assert latest_semver(["latest", "develop"]) is None

    def test_empty_list(self):
        assert latest_semver([]) is None


class TestVersionCache:
    """Tests for in-memory version cache."""

    def test_get_set(self):
        cache = VersionCache(ttl_seconds=3600)
        assert cache.get() is None
        cache.set("0.5.0")
        assert cache.get() == "0.5.0"

    def test_expiry(self):
        cache = VersionCache(ttl_seconds=0)  # Expire immediately
        cache.set("0.5.0")
        time.sleep(0.01)
        assert cache.get() is None

    def test_last_checked(self):
        cache = VersionCache()
        assert cache.last_checked is None
        cache.set("0.5.0")
        assert cache.last_checked is not None

    def test_clear(self):
        cache = VersionCache()
        cache.set("0.5.0")
        cache.clear()
        assert cache.get() is None
        assert cache.last_checked is None


class TestGhcrTagFetcher:
    """Tests for GHCR tag fetcher with mocked HTTP."""

    def test_fetch_tags_success(self):
        from app.adapters.version_check.ghcr import GhcrTagFetcher

        fetcher = GhcrTagFetcher(owner="test", repo="test")
        mock_response = MagicMock()
        mock_response.json.return_value = {"tags": ["0.4.5", "0.5.0", "latest"]}
        mock_response.raise_for_status.return_value = None

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            tags = fetcher.fetch_tags("backend")

        assert tags == ["0.4.5", "0.5.0", "latest"]

    def test_fetch_tags_http_error(self):
        from app.adapters.version_check.ghcr import GhcrTagFetcher

        fetcher = GhcrTagFetcher(owner="test", repo="test")

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception(
                "Connection error"
            )
            tags = fetcher.fetch_tags("backend")

        assert tags == []

    def test_fetch_latest_version(self):
        from app.adapters.version_check.ghcr import GhcrTagFetcher

        fetcher = GhcrTagFetcher(owner="test", repo="test")
        mock_response = MagicMock()
        mock_response.json.return_value = {"tags": ["0.4.5", "0.5.0"]}
        mock_response.raise_for_status.return_value = None

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            latest = fetcher.fetch_latest_version("backend")

        assert latest == "0.5.0"


class TestCheckVersionTask:
    """Tests for check_version Celery task."""

    def test_check_version_success(self):
        from app.application.tasks import check_version

        with (
            patch(
                "app.adapters.version_check.ghcr.GhcrTagFetcher.fetch_latest_version"
            ) as mock_fetch,
            patch("app.adapters.version_check.cache.version_cache.set") as mock_set,
        ):
            mock_fetch.return_value = "0.5.0"
            result = check_version()

        assert result == {"latest": "0.5.0"}
        mock_fetch.assert_called_once_with("backend")
        mock_set.assert_called_once_with("0.5.0")

    def test_check_version_no_newer(self):
        from app.application.tasks import check_version

        with (
            patch(
                "app.adapters.version_check.ghcr.GhcrTagFetcher.fetch_latest_version"
            ) as mock_fetch,
            patch("app.adapters.version_check.cache.version_cache.set") as mock_set,
        ):
            mock_fetch.return_value = None
            result = check_version()

        assert result == {"latest": None}
        mock_set.assert_called_once_with(None)


class TestTriggerDockerUpdateTask:
    """Tests for trigger_docker_update Celery task."""

    def test_no_compose_dir(self):
        from app.application.tasks import trigger_docker_update

        with patch("app.config.settings.docker_compose_dir", ""):
            result = trigger_docker_update()

        assert result["status"] == "error"

    def test_compose_dir_not_found(self):
        from app.application.tasks import trigger_docker_update

        with patch("app.config.settings.docker_compose_dir", "/nonexistent/path"):
            result = trigger_docker_update()

        assert result["status"] == "error"

    @patch("subprocess.run")
    def test_update_success(self, mock_run):
        from app.application.tasks import trigger_docker_update

        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        with patch("app.config.settings.docker_compose_dir", "/tmp"):
            result = trigger_docker_update()

        assert result["status"] == "ok"
        assert result["details"]["pull"] == "ok"
        assert result["details"]["up"] == "ok"

    @patch("subprocess.run")
    def test_update_pull_fails(self, mock_run):
        from app.application.tasks import trigger_docker_update

        # First call (pull) fails, second call shouldn't be reached
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="network error"),
        ]

        with patch("app.config.settings.docker_compose_dir", "/tmp"):
            result = trigger_docker_update()

        assert result["status"] == "error"
        assert "failed" in result["details"]["pull"]
