# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Unassigned service slots (LÜCKEN) and which of them still need a notification.

A gap is reportable once while it stays open. Its identity is the business
key ``(district, date, congregation, slot)``: when the gap closes, or the slot
moves to another date or congregation, the old report is forgotten, so a gap
that opens again is reported again.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GapKey:
    district_id: UUID
    service_date: date
    congregation_id: UUID | None
    planning_slot_id: UUID


@dataclass(frozen=True, slots=True)
class SlotGap:
    key: GapKey
    event_title: str
    congregation_name: str


@dataclass(frozen=True, slots=True)
class GapChanges:
    opened: tuple[SlotGap, ...]
    closed: tuple[GapKey, ...]


def gap_changes(current: Iterable[SlotGap], reported: Iterable[GapKey]) -> GapChanges:
    """Gaps to report now and reports to forget, both in a stable order."""
    current_by_key = {gap.key: gap for gap in current}
    reported_keys = set(reported)
    opened = sorted(
        (gap for key, gap in current_by_key.items() if key not in reported_keys),
        key=_order,
    )
    closed = sorted(reported_keys - current_by_key.keys(), key=_key_order)
    return GapChanges(tuple(opened), tuple(closed))


def _key_order(key: GapKey) -> tuple:
    return (
        str(key.district_id),
        key.service_date,
        str(key.congregation_id),
        str(key.planning_slot_id),
    )


def _order(gap: SlotGap) -> tuple:
    return _key_order(gap.key)
