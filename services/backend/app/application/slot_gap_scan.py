"""Daily scan that reports newly opened service gaps (SLOT_UNASSIGNED).

Gaps exist only implicitly (a slot without assignment), so there is no state
change to emit an event from. The scan compares today's gaps with the ledger
of reported ones: new gaps are reported once, closed ones are forgotten so a
gap that opens again is reported again.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.event_payloads import slot_unassigned
from app.domain.events import DomainEvent
from app.domain.ports.slot_gaps import SlotGapLedger
from app.domain.slot_gaps import gap_changes

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScanSummary:
    open: int
    reported: int
    closed: int


class SlotGapScanner:
    def __init__(
        self,
        ledger: SlotGapLedger,
        publish: Callable[[DomainEvent], None],
        horizon_days: int,
    ) -> None:
        if horizon_days < 0:
            raise ValueError(f"horizon_days must not be negative, got {horizon_days}")
        self._ledger = ledger
        self._publish = publish
        self._horizon = timedelta(days=horizon_days)

    async def scan(self, today: date) -> ScanSummary:
        gaps = await self._ledger.open_gaps(today, today + self._horizon)
        changes = gap_changes(gaps, await self._ledger.reported())
        # Past gaps leave the window and are forgotten like closed ones; they
        # cannot reopen in the future.
        await self._ledger.forget(changes.closed)
        await self._ledger.mark_reported(changes.opened)
        for gap in changes.opened:
            self._publish(
                slot_unassigned(
                    gap.key.district_id,
                    congregation_name=gap.congregation_name,
                    service_date=gap.key.service_date,
                    event_title=gap.event_title,
                )
            )
        summary = ScanSummary(
            open=len(gaps), reported=len(changes.opened), closed=len(changes.closed)
        )
        logger.info("Slot gap scan: %s", summary)
        return summary
