# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""PlanningSlot.distribute_to: UC-04 congregation distribution rules."""

from __future__ import annotations

import uuid
from datetime import date, time

import pytest

from app.domain.models.planning_slot import (
    APPLICABILITY_ALL,
    InvalidApplicabilityError,
    PlanningSlot,
)

CONGREGATION_A = uuid.uuid4()
CONGREGATION_B = uuid.uuid4()
DISTRICT_CONGREGATIONS = {CONGREGATION_A, CONGREGATION_B}


def _slot(*, congregation_id: uuid.UUID | None = None) -> PlanningSlot:
    return PlanningSlot.create(
        district_id=uuid.uuid4(),
        planning_date=date(2026, 12, 24),
        planning_time=time(18, 0),
        congregation_id=congregation_id,
        applicability=["previous"],
    )


def test_all_sentinel_distributes_to_every_congregation() -> None:
    slot = _slot()
    slot.distribute_to([APPLICABILITY_ALL], DISTRICT_CONGREGATIONS)
    assert slot.applicability == ["all"]


def test_explicit_congregations_are_canonical_and_deduplicated_in_order() -> None:
    slot = _slot()
    slot.distribute_to(
        [str(CONGREGATION_B), f" {CONGREGATION_A} ", str(CONGREGATION_B).upper()],
        DISTRICT_CONGREGATIONS,
    )
    assert slot.applicability == [str(CONGREGATION_B), str(CONGREGATION_A)]


def test_empty_list_removes_distribution() -> None:
    slot = _slot()
    slot.distribute_to([], DISTRICT_CONGREGATIONS)
    assert slot.applicability == []


def test_duplicate_all_sentinel_is_accepted() -> None:
    slot = _slot()
    slot.distribute_to(["all", "all"], DISTRICT_CONGREGATIONS)
    assert slot.applicability == ["all"]


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        (["all", str(CONGREGATION_A)], "nicht mit einzelnen Gemeinden"),
        (["not-a-uuid"], "Ungültige Gemeinde-ID"),
        ([""], "Leere Gemeinde-IDs"),
        ([str(uuid.uuid4())], "gehört nicht zum Bezirk"),
    ],
    ids=["all-mixed", "malformed", "blank", "foreign-congregation"],
)
def test_invalid_distribution_is_rejected_without_side_effects(entries, message) -> None:
    slot = _slot()
    with pytest.raises(InvalidApplicabilityError, match=message):
        slot.distribute_to(entries, DISTRICT_CONGREGATIONS)
    assert slot.applicability == ["previous"]


def test_congregation_level_event_cannot_be_distributed() -> None:
    slot = _slot(congregation_id=CONGREGATION_A)
    with pytest.raises(InvalidApplicabilityError, match="Nur Bezirksveranstaltungen"):
        slot.distribute_to([APPLICABILITY_ALL], DISTRICT_CONGREGATIONS)


def test_congregation_level_event_may_clear_distribution() -> None:
    slot = _slot(congregation_id=CONGREGATION_A)
    slot.distribute_to([], DISTRICT_CONGREGATIONS)
    assert slot.applicability == []


def test_blank_entries_are_rejected() -> None:
    slot = _slot()
    with pytest.raises(InvalidApplicabilityError, match="Leere Gemeinde-IDs"):
        slot.distribute_to([str(CONGREGATION_A), "  "], DISTRICT_CONGREGATIONS)
    assert slot.applicability == ["previous"]
