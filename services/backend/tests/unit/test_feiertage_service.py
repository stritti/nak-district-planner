"""Unit tests for feiertage_service module."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.feiertage_service import (
    ENTSCHLAFENEN_MONATE,
    KIRCHLICHE_FESTTAGE,
    _content_hash,
    _easter_sunday,
    _external_uid,
    _first_sunday,
    _parse_day,
    import_feiertage,
    import_kirchliche_festtage,
    reference_feiertage_for_congregation,
)
from app.domain.models.planning_slot import PlanningSlot


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

    def test_easter_2027(self):
        """Easter Sunday 2027 should be March 28."""
        easter = _easter_sunday(2027)
        assert easter == date(2027, 3, 28)

    def test_easter_2028(self):
        """Easter Sunday 2028 should be April 16."""
        easter = _easter_sunday(2028)
        assert easter == date(2028, 4, 16)

    def test_easter_2029(self):
        """Easter Sunday 2029 should be April 1."""
        easter = _easter_sunday(2029)
        assert easter == date(2029, 4, 1)

    def test_easter_2030(self):
        """Easter Sunday 2030 should be April 21."""
        easter = _easter_sunday(2030)
        assert easter == date(2030, 4, 21)


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

    def _festtag_slots(self, district_id: uuid.UUID) -> dict[date, PlanningSlot]:
        """Return one existing slot per festtag date for 2026 (idempotent state)."""
        easter = _easter_sunday(2026)
        slots: dict[date, PlanningSlot] = {}
        for name, offset in KIRCHLICHE_FESTTAGE:
            day = easter + timedelta(days=offset)
            slots[day] = PlanningSlot.create(
                district_id=district_id,
                planning_date=day,
                planning_time=time(0, 0),
                category="Feiertag",
                title=name,
            )
        for name, month in ENTSCHLAFENEN_MONATE:
            day = _first_sunday(2026, month)
            slots[day] = PlanningSlot.create(
                district_id=district_id,
                planning_date=day,
                planning_time=time(0, 0),
                category="Feiertag",
                title=name,
            )
        return slots

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

    async def test_import_kirchliche_festtage_skips_existing_unchanged(self):
        """Existing slots with same title/date should be skipped (idempotent)."""
        district_id = uuid.uuid4()
        session = AsyncMock()

        existing_by_date = self._festtag_slots(district_id)

        slot_repo_mock = AsyncMock()
        slot_repo_mock.list_for_date_range.side_effect = lambda district_id, from_date, to_date: [
            existing_by_date.get(from_date)
        ]
        slot_repo_mock.save.return_value = None

        with patch(
            "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=slot_repo_mock
        ):
            result = await import_kirchliche_festtage(district_id, 2026, session)

        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["skipped"] == 6  # 3 kirchliche Festtage + 3 Entschlafenen
        slot_repo_mock.save.assert_not_called()

    async def test_import_kirchliche_festtage_updates_changed_events(self):
        """Existing slots with different title should be updated."""
        district_id = uuid.uuid4()
        session = AsyncMock()

        existing_by_date = self._festtag_slots(district_id)
        easter = _easter_sunday(2026)
        # Corrupt the Ostersonntag slot: wrong title (repository returns it for easter date)
        existing_by_date[easter] = PlanningSlot.create(
            district_id=district_id,
            planning_date=easter,
            planning_time=time(0, 0),
            category="Feiertag",
            title="Falscher Titel",
        )

        # Build a list of all existing slots for the district
        all_existing = list(existing_by_date.values())

        slot_repo_mock = AsyncMock()
        # Repository-faithful: only return slots whose planning_date falls within the range
        slot_repo_mock.list_for_date_range.side_effect = lambda district_id, from_date, to_date: [
            s for s in all_existing if from_date <= s.planning_date <= to_date
        ]
        slot_repo_mock.save.return_value = None

        with patch(
            "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=slot_repo_mock
        ):
            result = await import_kirchliche_festtage(district_id, 2026, session)

        # With repository-faithful mocking, the wrong-date slot is NOT found for easter date,
        # so a new slot is created for Ostersonntag. The other 5 slots match and are skipped.
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["skipped"] == 5
        slot_repo_mock.save.assert_called_once()


class TestImportFeiertage:
    """Tests for import_feiertage() — Nager.Date API + state filtering."""

    def _mock_nager_client(self, holidays: list[dict]):
        """Patch httpx.AsyncClient to return the given Nager.Date payload."""
        resp_mock = MagicMock()
        resp_mock.json.return_value = holidays
        resp_mock.raise_for_status.return_value = None

        client_mock = MagicMock()
        client_mock.get = AsyncMock(return_value=resp_mock)

        async_client_mock = MagicMock()
        async_client_mock.__aenter__.return_value = client_mock
        async_client_mock.__aexit__.return_value = None
        return patch(
            "app.application.feiertage_service.httpx.AsyncClient", return_value=async_client_mock
        )

    async def test_import_feiertage_creates_national_holidays(self):
        """National holidays (counties=None) should be imported."""
        district_id = uuid.uuid4()
        session = AsyncMock()
        holidays = [
            {"date": "2026-01-01", "localName": "Neujahr", "counties": None},
            {"date": "2026-10-03", "localName": "Tag der Deutschen Einheit", "counties": None},
        ]

        slot_repo_mock = AsyncMock()
        slot_repo_mock.list_for_date_range.return_value = []
        slot_repo_mock.save.return_value = None

        with self._mock_nager_client(holidays), patch(
            "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=slot_repo_mock
        ):
            result = await import_feiertage(district_id, 2026, None, session)

        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["skipped"] == 0
        assert slot_repo_mock.save.call_count == 2

    async def test_import_feiertage_filters_by_state_code(self):
        """Only national + matching-state holidays should be imported."""
        district_id = uuid.uuid4()
        session = AsyncMock()
        holidays = [
            {"date": "2026-01-01", "localName": "Neujahr", "counties": None},
            {"date": "2026-01-06", "localName": "Heilige Drei Könige", "counties": ["DE-BW", "DE-BY"]},
            {"date": "2026-08-15", "localName": "Mariä Himmelfahrt", "counties": ["DE-BY"]},
            {"date": "2026-11-01", "localName": "Allerheiligen", "counties": ["DE-NW"]},
        ]

        slot_repo_mock = AsyncMock()
        slot_repo_mock.list_for_date_range.return_value = []
        slot_repo_mock.save.return_value = None

        with self._mock_nager_client(holidays), patch(
            "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=slot_repo_mock
        ):
            result = await import_feiertage(district_id, 2026, "BY", session)

        assert result["created"] == 3  # Neujahr + Heilige Drei Könige + Mariä Himmelfahrt
        assert result["updated"] == 0
        assert result["skipped"] == 0
        # Allerheiligen (NW-only) must not be imported
        saved_titles = [call.args[0].title for call in slot_repo_mock.save.call_args_list]
        assert "Allerheiligen" not in saved_titles

    async def test_import_feiertage_idempotent_second_run(self):
        """Re-importing the same year must not create duplicates."""
        district_id = uuid.uuid4()
        session = AsyncMock()
        holidays = [{"date": "2026-01-01", "localName": "Neujahr", "counties": None}]

        existing = PlanningSlot.create(
            district_id=district_id,
            planning_date=date(2026, 1, 1),
            planning_time=time(0, 0),
            category="Feiertag",
            title="Neujahr",
        )
        slot_repo_mock = AsyncMock()
        slot_repo_mock.list_for_date_range.return_value = [existing]
        slot_repo_mock.save.return_value = None

        with self._mock_nager_client(holidays), patch(
            "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=slot_repo_mock
        ):
            result = await import_feiertage(district_id, 2026, None, session)

        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["skipped"] == 1
        slot_repo_mock.save.assert_not_called()


class TestReferenceFeiertageForCongregation:
    """Tests for reference_feiertage_for_congregation() function."""

    def _slot(
        self,
        district_id: uuid.UUID,
        *,
        congregation_id: uuid.UUID | None,
        category: str,
        applicability: list[str] | None = None,
    ) -> PlanningSlot:
        return PlanningSlot.create(
            district_id=district_id,
            planning_date=date(2026, 4, 5),
            planning_time=time(0, 0),
            congregation_id=congregation_id,
            category=category,
            title="Test",
            applicability=applicability,
        )

    async def test_references_only_district_holidays(self):
        """Only district-level Feiertag slots should get the congregation reference."""
        district_id = uuid.uuid4()
        congregation_id = uuid.uuid4()
        session = AsyncMock()

        district_holiday = self._slot(district_id, congregation_id=None, category="Feiertag")
        congregation_holiday = self._slot(
            district_id, congregation_id=congregation_id, category="Feiertag"
        )
        district_service = self._slot(district_id, congregation_id=None, category="Gottesdienst")

        slot_repo_mock = AsyncMock()
        slot_repo_mock.list_for_date_range.return_value = [
            district_holiday,
            congregation_holiday,
            district_service,
        ]
        slot_repo_mock.save.return_value = None

        with patch(
            "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=slot_repo_mock
        ):
            updated = await reference_feiertage_for_congregation(
                district_id, congregation_id, session
            )

        assert updated == 1
        assert str(congregation_id) in district_holiday.applicability
        assert str(congregation_id) not in congregation_holiday.applicability
        assert str(congregation_id) not in district_service.applicability
        slot_repo_mock.save.assert_called_once_with(district_holiday)

    async def test_skips_when_already_referenced(self):
        """Slots that already reference the congregation must not be updated."""
        district_id = uuid.uuid4()
        congregation_id = uuid.uuid4()
        session = AsyncMock()

        district_holiday = self._slot(
            district_id,
            congregation_id=None,
            category="Feiertag",
            applicability=[str(congregation_id)],
        )

        slot_repo_mock = AsyncMock()
        slot_repo_mock.list_for_date_range.return_value = [district_holiday]
        slot_repo_mock.save.return_value = None

        with patch(
            "app.application.feiertage_service.SqlPlanningSlotRepository", return_value=slot_repo_mock
        ):
            updated = await reference_feiertage_for_congregation(
                district_id, congregation_id, session
            )

        assert updated == 0
        slot_repo_mock.save.assert_not_called()
