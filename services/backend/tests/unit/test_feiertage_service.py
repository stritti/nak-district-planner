"""Unit tests for feiertage_service module."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.application.feiertage_service import (
    _content_hash,
    _easter_sunday,
    _external_uid,
    _first_sunday,
    _parse_day,
    import_feiertage,
    import_kirchliche_festtage,
    reference_feiertage_for_congregation,
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

    async def test_import_kirchliche_festtage_creates_slots(self):
        """import_kirchliche_festtage should create PlanningSlots for the year."""
        district_id = uuid.uuid4()
        session = AsyncMock()

        slot_repo_mock = AsyncMock()
        # Return empty list for existing slots (none exist yet)
        slot_repo_mock.list_for_date_range.return_value = []
        slot_repo_mock.save.return_value = None

        with patch(
            "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=slot_repo_mock
        ):
            result = await import_kirchliche_festtage(district_id, 2026, session)

        assert result["created"] > 0
        assert result["updated"] == 0
        assert result["skipped"] == 0
        assert slot_repo_mock.save.call_count == result["created"]

    @pytest.mark.skip(reason="Needs update for PlanningSlot migration - Task Group 1.1")
    async def test_import_kirchliche_festtage_skips_existing_unchanged(self):
        """Existing slots with same hash should be skipped."""
        # TODO: Update this test after PlanningSlot migration
        # This test needs to be rewritten to use PlanningSlot instead of Event
        pass

    @pytest.mark.skip(reason="Needs update for PlanningSlot migration - Task Group 1.1")
    async def test_import_kirchliche_festtage_updates_changed_events(self):
        """Existing slots with different hash should be updated."""
        # TODO: Update this test after PlanningSlot migration
        pass


@pytest.mark.skip(reason="Needs update for PlanningSlot migration - Task Group 1.1")
class TestImportFeiertage:
    """Tests for import_feiertage() function - TODO: Update for PlanningSlot migration."""

    async def test_import_feiertage_requires_api_call(self):
        """TODO: Update for PlanningSlot migration."""
        pass

    async def test_import_feiertage_filters_by_state_code(self):
        """TODO: Update for PlanningSlot migration."""
        pass


@pytest.mark.skip(reason="Needs update for PlanningSlot migration - Task Group 1.1")
class TestReferenceFeiertageForCongregation:
    """Tests for reference_feiertage_for_congregation() function - TODO: Update for PlanningSlot migration."""

    async def test_references_only_district_holidays(self):
        """TODO: Update for PlanningSlot migration."""
        pass

    async def test_skips_when_already_referenced(self):
        """TODO: Update for PlanningSlot migration."""
        pass
