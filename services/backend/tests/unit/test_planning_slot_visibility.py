"""Unit tests for the shared planning-slot visibility rules (issue #466)."""

from __future__ import annotations

import uuid
from datetime import date, time

import pytest

from app.domain.models.export_token import ExportToken, TokenType
from app.domain.models.planning_slot import (
    APPLICABILITY_ALL,
    EventApprovalStatus,
    PlanningSlot,
)

DISTRICT = uuid.uuid4()
CONG_A = uuid.uuid4()
CONG_B = uuid.uuid4()


def _slot(
    *,
    congregation_id: uuid.UUID | None = None,
    applicability: list[str] | None = None,
    approval_status: EventApprovalStatus | None = EventApprovalStatus.CONFIRMED,
) -> PlanningSlot:
    return PlanningSlot.create(
        district_id=DISTRICT,
        planning_date=date(2026, 8, 16),
        planning_time=time(10, 0),
        congregation_id=congregation_id,
        applicability=applicability,
        approval_status=approval_status,
    )


def test_own_congregation_slot_is_visible_only_to_owner() -> None:
    slot = _slot(congregation_id=CONG_A)
    assert slot.is_visible_to(CONG_A)
    assert not slot.is_visible_to(CONG_B)


def test_own_slot_ignores_applicability() -> None:
    slot = _slot(congregation_id=CONG_A, applicability=[APPLICABILITY_ALL])
    assert not slot.is_visible_to(CONG_B)


@pytest.mark.parametrize(
    ("applicability", "visible_to_a", "visible_to_b"),
    [
        ([], False, False),
        ([APPLICABILITY_ALL], True, True),
        ([str(CONG_A)], True, False),
    ],
)
def test_district_slot_visibility_follows_applicability(
    applicability: list[str], visible_to_a: bool, visible_to_b: bool
) -> None:
    slot = _slot(applicability=applicability)
    assert slot.is_visible_to(CONG_A) is visible_to_a
    assert slot.is_visible_to(CONG_B) is visible_to_b


@pytest.mark.parametrize(
    ("approval_status", "distributed"),
    [
        (EventApprovalStatus.CONFIRMED, True),
        (EventApprovalStatus.PLANNED, False),
        (None, False),
    ],
)
def test_district_slot_is_distributed_only_when_confirmed(
    approval_status: EventApprovalStatus | None, distributed: bool
) -> None:
    slot = _slot(applicability=[APPLICABILITY_ALL], approval_status=approval_status)
    assert slot.is_distributed_to(CONG_A) is distributed


def test_own_slot_is_not_a_distribution() -> None:
    assert not _slot(congregation_id=CONG_A).is_distributed_to(CONG_A)


def _token(token_type: TokenType, leader_id: uuid.UUID | None = None) -> ExportToken:
    return ExportToken.create(
        label="t",
        token_type=token_type,
        district_id=DISTRICT,
        congregation_id=None,
        leader_id=leader_id,
    )


@pytest.mark.parametrize("requested", [None, "confirmed_only", "include_planned"])
@pytest.mark.parametrize("leader_id", [None, uuid.uuid4()])
def test_public_token_always_exports_confirmed_only(
    requested: str | None, leader_id: uuid.UUID | None
) -> None:
    assert _token(TokenType.PUBLIC, leader_id).confirmed_only(requested) is True


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(None, False), ("include_planned", False), ("confirmed_only", True)],
)
def test_internal_token_honours_requested_filter(requested: str | None, expected: bool) -> None:
    assert _token(TokenType.INTERNAL).confirmed_only(requested) is expected
