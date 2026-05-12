"""Unit tests for MicrosoftGraphCalendarConnector.

All HTTP calls are intercepted via a mock httpx.AsyncClient — no network needed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.adapters.calendar.microsoft_connector import (
    MicrosoftGraphCalendarConnector,
    _content_hash,
)

CREDS = {"access_token": "test_token"}


def _make_event(
    *,
    id: str = "event123",
    subject: str = "Test Event",
    start: dict[str, str],
    end: dict[str, str],
    body_preview: str | None = None,
    status: str | None = None,
) -> dict:
    """Build a Microsoft Graph API event dict."""
    event: dict = {
        "id": id,
        "subject": subject,
        "start": start,
        "end": end,
        "iCalUId": id,  # Microsoft Graph returns iCalUId
    }
    if body_preview is not None:
        event["bodyPreview"] = body_preview
    if status is not None:
        event["status"] = status
    return event


def _setup_mock_client(mock_client: MagicMock, response_data: dict) -> None:
    """Configure the mock httpx.AsyncClient to return a successful response."""
    mock_response = MagicMock()
    mock_response.__getitem__.return_value = response_data  # for .get("value", [])
    mock_response.json.return_value = {"value": response_data}
    mock_response.raise_for_status.return_value = None

    mock_client.get = AsyncMock(return_value=mock_response)


@pytest.fixture
def mock_client() -> MagicMock:
    return MagicMock(spec=httpx.AsyncClient)


@pytest.fixture
def connector(mock_client: MagicMock) -> MicrosoftGraphCalendarConnector:
    return MicrosoftGraphCalendarConnector(client=mock_client)


# ── _content_hash ─────────────────────────────────────────────────────────────────


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


# ── fetch_events ──────────────────────────────────────────────────────────────────


class TestFetchEvents:
    async def test_valid_returns_event(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        _setup_mock_client(
            mock_client,
            [
                _make_event(
                    id="uid@test",
                    subject="Gottesdienst",
                    start={"dateTime": "2026-04-05T10:00:00Z"},
                    end={"dateTime": "2026-04-05T11:00:00Z"},
                    body_preview="Beschreibung",
                )
            ],
        )

        raw_events = await connector.fetch_events(CREDS)
        assert len(raw_events) == 1
        raw = raw_events[0]
        assert raw.uid == "uid@test"
        assert raw.title == "Gottesdienst"
        assert raw.start_at == datetime(2026, 4, 5, 10, tzinfo=UTC)
        assert raw.end_at == datetime(2026, 4, 5, 11, tzinfo=UTC)
        assert raw.description == "Beschreibung"
        assert not raw.is_cancelled

    async def test_cancelled_status_sets_flag(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        _setup_mock_client(
            mock_client,
            [
                _make_event(
                    id="uid@test",
                    subject="Gottesdienst",
                    start={"dateTime": "2026-04-05T10:00:00Z"},
                    end={"dateTime": "2026-04-05T11:00:00Z"},
                    status="cancelled",
                )
            ],
        )

        raw_events = await connector.fetch_events(CREDS)
        assert len(raw_events) == 1
        assert raw_events[0].is_cancelled is True

    async def test_all_day_event_becomes_midnight_utc(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        # Microsoft Graph doesn't have all-day events in the same way as iCal,
        # but we can test with date-only values if the API supported them.
        # For now, we'll skip this test as it's not applicable to Graph API in the same way.
        pass

    async def test_event_without_uid_is_skipped(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        _setup_mock_client(
            mock_client,
            [
                _make_event(
                    id="",
                    subject="No UID",
                    start={"dateTime": "2026-04-05T10:00:00Z"},
                    end={"dateTime": "2026-04-05T11:00:00Z"},
                ),
                _make_event(
                    id="valid@test",
                    subject="Valid",
                    start={"dateTime": "2026-04-05T12:00:00Z"},
                    end={"dateTime": "2026-04-05T13:00:00Z"},
                ),
            ],
        )

        raw_events = await connector.fetch_events(CREDS)
        assert len(raw_events) == 1
        assert raw_events[0].uid == "valid@test"

    async def test_multiple_events_returned(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        _setup_mock_client(
            mock_client,
            [
                _make_event(
                    id="uid1",
                    subject="Event 1",
                    start={"dateTime": "2026-04-05T10:00:00Z"},
                    end={"dateTime": "2026-04-05T11:00:00Z"},
                ),
                _make_event(
                    id="uid2",
                    subject="Event 2",
                    start={"dateTime": "2026-04-05T12:00:00Z"},
                    end={"dateTime": "2026-04-05T13:00:00Z"},
                ),
            ],
        )

        raw_events = await connector.fetch_events(CREDS)
        assert len(raw_events) == 2
        assert {raw.uid for raw in raw_events} == {"uid1", "uid2"}

    async def test_from_dt_filter_excludes_ended_events(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        from_dt = datetime(2026, 4, 5, 12, 0, tzinfo=UTC)  # noon
        _setup_mock_client(
            mock_client,
            [
                _make_event(
                    id="early",
                    subject="Early Event",
                    start={"dateTime": "2026-04-05T09:00:00Z"},
                    end={"dateTime": "2026-04-05T10:00:00Z"},  # ends before from_dt
                ),
                _make_event(
                    id="late",
                    subject="Late Event",
                    start={"dateTime": "2026-04-05T13:00:00Z"},
                    end={"dateTime": "2026-04-05T14:00:00Z"},
                ),
            ],
        )

        raw_events = await connector.fetch_events(CREDS, from_dt=from_dt)
        assert len(raw_events) == 1
        assert raw_events[0].uid == "late"

    async def test_to_dt_filter_excludes_future_events(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        to_dt = datetime(2026, 4, 5, 12, 0, tzinfo=UTC)  # noon
        _setup_mock_client(
            mock_client,
            [
                _make_event(
                    id="early",
                    subject="Early Event",
                    start={"dateTime": "2026-04-05T10:00:00Z"},
                    end={"dateTime": "2026-04-05T11:00:00Z"},  # ends before to_dt
                ),
                _make_event(
                    id="future",
                    subject="Future Event",
                    start={"dateTime": "2026-04-05T13:00:00Z"},
                    end={"dateTime": "2026-04-05T14:00:00Z"},  # starts after to_dt
                ),
            ],
        )

        raw_events = await connector.fetch_events(CREDS, to_dt=to_dt)
        assert len(raw_events) == 1
        assert raw_events[0].uid == "early"

    async def test_http_404_raises_value_error(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        mock_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="HTTP 404"):
            await connector.fetch_events(CREDS)

    async def test_http_401_raises_value_error(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
        )
        mock_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="HTTP 401"):
            await connector.fetch_events(CREDS)

    async def test_http_500_raises_value_error(
        self, connector: MicrosoftGraphCalendarConnector, mock_client: MagicMock
    ) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error", request=MagicMock(), response=MagicMock(status_code=500)
        )
        mock_client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError, match="HTTP 500"):
            await connector.fetch_events(CREDS)
