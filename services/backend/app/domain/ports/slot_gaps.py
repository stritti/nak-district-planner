"""Port for finding unassigned slots and remembering which were reported."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date

from app.domain.slot_gaps import GapKey, SlotGap


class SlotGapLedger(ABC):
    @abstractmethod
    async def open_gaps(self, from_date: date, to_date: date) -> Sequence[SlotGap]:
        """Active service slots without assignment in ``[from_date, to_date]``."""

    @abstractmethod
    async def reported(self) -> Sequence[GapKey]:
        """Gaps already reported and not closed since."""

    @abstractmethod
    async def mark_reported(self, gaps: Sequence[SlotGap]) -> None:
        """Remember ``gaps`` as reported while they stay open."""

    @abstractmethod
    async def forget(self, keys: Sequence[GapKey]) -> None:
        """Drop reports whose gap closed, so a reopened gap is reported again."""
