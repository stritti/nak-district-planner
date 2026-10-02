"""Daily SLOT_UNASSIGNED scan: report each open gap once, again after reopening."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application import slot_gap_tasks
from app.application.slot_gap_scan import ScanSummary, SlotGapScanner
from app.domain.events import EventType
from app.domain.models.event_mail_hook import EVENT_PLACEHOLDERS
from app.domain.ports.slot_gaps import SlotGapLedger
from app.domain.slot_gaps import GapKey, SlotGap, gap_changes

DISTRICT = uuid.uuid4()
CONGREGATION = uuid.uuid4()
TODAY = date(2026, 10, 1)


def _gap(day: int = 4, slot: uuid.UUID | None = None, congregation=CONGREGATION) -> SlotGap:
    return SlotGap(
        key=GapKey(DISTRICT, date(2026, 10, day), congregation, slot or uuid.uuid4()),
        event_title="Gottesdienst",
        congregation_name="Gemeinde Süd",
    )


class InMemoryLedger(SlotGapLedger):
    def __init__(self, gaps=()) -> None:
        self.gaps = list(gaps)
        self.keys: set[GapKey] = set()
        self.windows: list[tuple[date, date]] = []

    async def open_gaps(self, from_date, to_date):
        self.windows.append((from_date, to_date))
        return [g for g in self.gaps if from_date <= g.key.service_date <= to_date]

    async def reported(self):
        return list(self.keys)

    async def mark_reported(self, gaps):
        self.keys |= {g.key for g in gaps}

    async def forget(self, keys):
        self.keys -= set(keys)


def _scanner(ledger, horizon_days: int = 28):
    published = []
    return SlotGapScanner(ledger, published.append, horizon_days), published


class TestGapChanges:
    def test_new_gaps_open_and_vanished_reports_close(self) -> None:
        kept, new = _gap(4), _gap(5)
        stale = _gap(6).key

        changes = gap_changes([kept, new], [kept.key, stale])

        assert changes.opened == (new,)
        assert changes.closed == (stale,)

    def test_moved_slot_is_a_new_gap_and_the_old_report_closes(self) -> None:
        slot = uuid.uuid4()
        before, after = _gap(4, slot), _gap(11, slot)

        changes = gap_changes([after], [before.key])

        assert changes.opened == (after,)
        assert changes.closed == (before.key,)

    def test_order_is_stable(self) -> None:
        gaps = [_gap(day) for day in (9, 4, 7)]
        assert [g.key.service_date.day for g in gap_changes(gaps, []).opened] == [4, 7, 9]


class TestScanner:
    async def test_reports_each_open_gap_once(self) -> None:
        ledger = InMemoryLedger([_gap(4), _gap(5)])
        scanner, published = _scanner(ledger)

        first = await scanner.scan(TODAY)
        second = await scanner.scan(TODAY)

        assert first == ScanSummary(open=2, reported=2, closed=0)
        assert second == ScanSummary(open=2, reported=0, closed=0)
        assert len(published) == 2

    async def test_closed_gap_is_reported_again_when_it_reopens(self) -> None:
        gap = _gap(4)
        ledger = InMemoryLedger([gap])
        scanner, published = _scanner(ledger)

        await scanner.scan(TODAY)
        ledger.gaps = []  # leader assigned
        closed = await scanner.scan(TODAY)
        ledger.gaps = [gap]  # assignment removed again
        reopened = await scanner.scan(TODAY)

        assert closed == ScanSummary(open=0, reported=0, closed=1)
        assert reopened.reported == 1
        assert len(published) == 2

    async def test_event_carries_the_slot_unassigned_payload(self) -> None:
        gap = _gap(4)
        scanner, published = _scanner(InMemoryLedger([gap]))

        await scanner.scan(TODAY)

        [event] = published
        assert (event.event_type, event.district_id) == (EventType.SLOT_UNASSIGNED, DISTRICT)
        assert dict(event.payload) == {
            "congregation_name": "Gemeinde Süd",
            "date": "2026-10-04",
            "event_title": "Gottesdienst",
        }
        # Every placeholder of the hook editor is filled (district_name by the dispatcher).
        assert (
            set(event.payload) | {"district_name"} == EVENT_PLACEHOLDERS[EventType.SLOT_UNASSIGNED]
        )

    async def test_scans_the_configured_window_from_today(self) -> None:
        ledger = InMemoryLedger([_gap(4), _gap(30)])
        scanner, _ = _scanner(ledger, horizon_days=7)

        summary = await scanner.scan(TODAY)

        assert ledger.windows == [(TODAY, date(2026, 10, 8))]
        assert summary.reported == 1

    def test_negative_horizon_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="horizon_days"):
            SlotGapScanner(InMemoryLedger(), print, -1)


class TestCeleryTask:
    def test_task_scans_with_sql_ledger_and_commits(self) -> None:
        session = MagicMock()
        session.commit = AsyncMock()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=session)
        factory.return_value.__aexit__ = AsyncMock(return_value=False)
        scan = AsyncMock(return_value=ScanSummary(open=3, reported=1, closed=2))

        with (
            patch("app.adapters.db.session.AsyncSessionLocal", factory),
            patch.object(SlotGapScanner, "scan", scan),
        ):
            result = slot_gap_tasks.scan_slot_gaps.run()

        assert result == {"open": 3, "reported": 1, "closed": 2}
        session.commit.assert_awaited_once()

    def test_scan_is_scheduled_daily(self) -> None:
        from app.celery_app import celery

        entry = celery.conf.beat_schedule["scan-slot-gaps"]
        assert entry["task"] == "scan_slot_gaps"
