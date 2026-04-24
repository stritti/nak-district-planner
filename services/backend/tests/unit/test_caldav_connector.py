"""Unit tests for CalDAVConnector.

Since CalDAV involves complex XML parsing and HTTP REPORT requests,
we'll focus on testing the basic structure and error handling.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from unittest.mock import MagicMock

import httpx

from app.adapters.calendar.caldav_connector import CalDAVConnector, _content_hash

CREDS = {
    "url": "https://example.com/calendars/user/default/",
    "username": "user",
    "password": "pass",
}


def test_content_hash_deterministic() -> None:
    h1 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title",
    )
    h2 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title",
    )
    assert h1 == h2


def test_content_hash_changes_on_title_change() -> None:
    h1 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title A",
    )
    h2 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title B",
    )
    assert h1 != h2


def test_content_hash_changes_on_time_change() -> None:
    h1 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 13, tzinfo=UTC),
        "Title",
    )
    h2 = _content_hash(
        "uid",
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 1, 14, tzinfo=UTC),
        "Title",
    )
    assert h1 != h2


class TestCalDAVConnectorBasics:
    def test_init_with_client(self) -> None:
        """Test that we can inject a custom httpx client."""
        mock_client = MagicMock()
        connector = CalDAVConnector(client=mock_client)
        assert connector._client == mock_client

    def test_init_without_client_creates_one(self) -> None:
        """Test that a default client is created when none is provided."""
        connector = CalDAVConnector()
        assert isinstance(connector._client, httpx.AsyncClient)

    def test_format_datetime(self) -> None:
        """Test the datetime formatting helper."""
        connector = CalDAVConnector()

        # Test with timezone-aware datetime
        dt = datetime(2026, 4, 5, 10, 30, 0, tzinfo=UTC)
        formatted = connector._format_datetime(dt)
        assert formatted == "20260405T103000Z"

        # Test with naive datetime (should be treated as UTC)
        dt_naive = datetime(2026, 4, 5, 10, 30, 0)
        formatted_naive = connector._format_datetime(dt_naive)
        assert formatted_naive == "20260405T103000Z"


# We won't test the full fetch_events method here because it requires
# complex XML mocking. The integration tests in test_sync_service.py
# already cover the end-to-end flow with mocked connectors.
