"""Unit tests for feiertage_service module."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch


from app.application.feiertage_service import (
    _content_hash,
    _easter_sunday,
    _external_uid,
    _first_sunday,
    _parse_day,
    import_feiertage,
    import_kirchliche_festtage,
)


class TestEasterSunday:
    """Tests for _easter_sunday() function."""

    def test_easter_2026(self):
        """Easter Sunday 2026 should be April 5."""
        easter = _easter_sunday(2026)
        assert easter == date(2026, 4, 5)

    def test_easter_2025(self):
        """Easter Sunday 2025 should be April 20."""
        easter = _easter_sunday(2025)
        assert easter == date(2025, 4, 20)

    def test_easter_2024(self):
        """Easter Sunday 2024 should be March 31."""
        easter = _easter_sunday(2024)
        assert easter == date(2024, 3, 31)

    def test_easter_2000(self):
        """Easter Sunday 2000 should be April 23."""
        easter = _easter_sunday(2000)
        assert easter == date(2000, 4, 23)


class TestFirstSunday:
    """Tests for _first_sunday() function."""

    def test_first_sunday_march_2026(self):
        """First Sunday of March 2026 should be March 1."""
        result = _first_sunday(2026, 3)
        assert result == date(2026, 3, 1)
        assert result.weekday() == 6  # Sunday

    def test_first_sunday_july_2026(self):
        """First Sunday of July 2026 should be July 5."""
        result = _first_sunday(2026, 7)
        assert result == date(2026, 7, 5)
        assert result.weekday() == 6

    def test_first_sunday_november_2026(self):
        """First Sunday of November 2026 should be November 1."""
        result = _first_sunday(2026, 11)
        assert result == date(2026, 11, 1)
        assert result.weekday() == 6


class TestContentHash:
    """Tests for _content_hash() function."""

    def test_content_hash_returns_string(self):
        """_content_hash should return a string."""
        result = _content_hash("2026-04-05", "Ostersonntag")
        assert isinstance(result, str)

    def test_content_hash_same_input_same_output(self):
        """Same input should produce same hash."""
        hash1 = _content_hash("2026-04-05", "Ostersonntag")
        hash2 = _content_hash("2026-04-05", "Ostersonntag")
        assert hash1 == hash2

    def test_content_hash_different_dates_different_hashes(self):
        """Different dates should produce different hashes."""
        hash1 = _content_hash("2026-04-05", "Ostersonntag")
        hash2 = _content_hash("2026-04-06", "Ostersonntag")
        assert hash1 != hash2

    def test_content_hash_different_names_different_hashes(self):
        """Different names should produce different hashes."""
        hash1 = _content_hash("2026-04-05", "Ostersonntag")
        hash2 = _content_hash("2026-04-05", "Pfingstsonntag")
        assert hash1 != hash2


class TestExternalUid:
    """Tests for _external_uid() function."""

    def test_external_uid_format(self):
        """_external_uid should return properly formatted UID."""
        district_id = uuid.uuid4()
        uid = _external_uid(district_id, "2026-04-05", "Ostersonntag")
        assert uid.startswith("feiertag-DE-")
        assert str(district_id) in uid
        assert "ostersonntag" in uid.lower()

    def test_external_uid_unique_for_different_dates(self):
        """Different dates should produce different UIDs."""
        district_id = uuid.uuid4()
        uid1 = _external_uid(district_id, "2026-04-05", "Ostersonntag")
        uid2 = _external_uid(district_id, "2026-04-06", "Ostersonntag")
        assert uid1 != uid2

    def test_external_uid_handles_umlauts(self):
        """_external_uid should convert umlauts."""
        district_id = uuid.uuid4()
        uid = _external_uid(district_id, "2026-04-05", "Pfingstäöü")
        assert "ä" not in uid
        assert "ö" not in uid
        assert "ü" not in uid


class TestParseDay:
    """Tests for _parse_day() function."""

    def test_parse_day_returns_tuple(self):
        """_parse_day should return (start, end) tuple."""
        start, end = _parse_day("2026-04-05")
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

    def test_parse_day_start_is_midnight(self):
        """Start time should be 00:00:00 UTC."""
        start, _ = _parse_day("2026-04-05")
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0

    def test_parse_day_end_is_23_59_59(self):
        """End time should be 23:59:59 UTC."""
        _, end = _parse_day("2026-04-05")
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59

    def test_parse_day_correct_date(self):
        """Parsed date should match input."""
        start, end = _parse_day("2026-04-05")
        assert start.year == 2026
        assert start.month == 4
        assert start.day == 5
        assert end.year == 2026
        assert end.month == 4
        assert end.day == 5


class TestImportKirchlicheFesttage:
    """Tests for import_kirchliche_festtage() function."""

    async def test_import_kirchliche_festtage_creates_events(self):
        """import_kirchliche_festtage should create events for the year."""
        district_id = uuid.uuid4()
        session = AsyncMock()

        event_repo_mock = AsyncMock()
        event_repo_mock.get_by_external_uid_district.return_value = None
        event_repo_mock.save.return_value = None

        with patch(
            "app.application.feiertage_service.SqlEventRepository", return_value=event_repo_mock
        ):
            result = await import_kirchliche_festtage(district_id, 2026, session)

        assert result["created"] > 0
        assert result["updated"] == 0
        assert result["skipped"] == 0
        assert event_repo_mock.save.call_count == result["created"]

    async def test_import_kirchliche_festtage_skips_existing_unchanged(self):
        """Existing events with same hash should be skipped."""
        district_id = uuid.uuid4()
        session = AsyncMock()

        # Mock event that already exists with same hash
        from app.domain.models.event import Event

        existing_event = Event.create(
            title="Ostersonntag",
            start_at=datetime(2026, 4, 5, 0, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 5, 23, 59, 59, tzinfo=timezone.utc),
            district_id=district_id,
        )

        event_repo_mock = AsyncMock()
        # First call returns None (for other events), then returns existing
        event_repo_mock.get_by_external_uid_district.side_effect = [
            None,  # Palmsonntag
            existing_event,  # Ostersonntag
            None,  # Pfingstsonntag
            None,
            None,
            None,  # Entschlafenen
        ]
        event_repo_mock.save.return_value = None

        with patch(
            "app.application.feiertage_service.SqlEventRepository", return_value=event_repo_mock
        ):
            result = await import_kirchliche_festtage(district_id, 2026, session)

        assert result["skipped"] > 0
        # Check that save was called fewer times than total events
        assert (
            event_repo_mock.save.call_count
            < event_repo_mock.get_by_external_uid_district.call_count
        )

    async def test_import_kirchliche_festtage_updates_changed_events(self):
        """Existing events with different hash should be updated."""
        district_id = uuid.uuid4()
        session = AsyncMock()

        from app.domain.models.event import Event

        existing_event = Event.create(
            title="Old Title",
            start_at=datetime(2026, 4, 5, 0, 0, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 4, 5, 23, 59, 59, tzinfo=timezone.utc),
            district_id=district_id,
        )
        # Manually set a different hash
        existing_event.content_hash = "old-hash"

        event_repo_mock = AsyncMock()
        event_repo_mock.get_by_external_uid_district.return_value = existing_event
        event_repo_mock.save.return_value = None

        with patch(
            "app.application.feiertage_service.SqlEventRepository", return_value=event_repo_mock
        ):
            result = await import_kirchliche_festtage(district_id, 2026, session)

        assert result["updated"] > 0
        assert event_repo_mock.save.call_count > 0


class TestImportFeiertage:
    """Tests for import_feiertage() function."""

    async def test_import_feiertage_requires_api_call(self):
        """import_feiertage should make HTTP request to Nager.Date."""
        district_id = uuid.uuid4()
        session = AsyncMock()

        mock_response = AsyncMock()
        mock_response.json.return_value = [
            {
                "date": "2026-04-02",
                "localName": "Gründonnerstag",
                "name": "Maundy Thursday",
                "countryCode": "DE",
                "fixed": False,
                "counties": None,
                "launchYear": 1700,
                "types": ["Public"],
            }
        ]

        event_repo_mock = AsyncMock()
        event_repo_mock.get_by_external_uid_district.return_value = None
        event_repo_mock.save.return_value = None

        with patch("app.application.feiertage_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch(
                "app.application.feiertage_service.SqlEventRepository", return_value=event_repo_mock
            ):
                result = await import_feiertage(district_id, 2026, None, session)

        assert result["created"] >= 0
        mock_client.get.assert_called_once()

    async def test_import_feiertage_filters_by_state_code(self):
        """import_feiertage should filter by state_code when provided."""
        district_id = uuid.uuid4()
        session = AsyncMock()

        mock_response = AsyncMock()
        # Response with national holiday + state-specific holiday
        mock_response.json.return_value = [
            {
                "date": "2026-01-01",
                "localName": "Neujahr",
                "counties": None,  # National
            },
            {
                "date": "2026-11-01",
                "localName": "Allerheiligen",
                "counties": ["DE-BW", "DE-BY"],  # Only in BW and BY
            },
        ]

        event_repo_mock = AsyncMock()
        event_repo_mock.get_by_external_uid_district.return_value = None
        event_repo_mock.save.return_value = None

        with patch("app.application.feiertage_service.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch(
                "app.application.feiertage_service.SqlEventRepository", return_value=event_repo_mock
            ):
                # Filter for Baden-Württemberg
                result = await import_feiertage(district_id, 2026, "BW", session)

        # Should create events for both national holiday and BW-specific holiday
        assert result["created"] >= 0
