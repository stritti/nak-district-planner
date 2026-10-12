# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Mapping and safe mutation regression tests for recurring-event repositories."""

from __future__ import annotations

import uuid
from datetime import date, time
from unittest.mock import AsyncMock, Mock

import pytest

from app.adapters.db.orm_models.recurring_event import (
    RecurringEventDecisionORM,
    RecurringEventTemplateORM,
)
from app.adapters.db.repositories.recurring_event import (
    SqlRecurringEventRepository,
    _decision_from_row,
    _template_from_row,
    _template_to_row,
)
from app.domain.models.recurring_event_template import (
    DecisionStatus,
    RecurrenceKind,
    RecurrenceRule,
    RecurringEventDecision,
    RecurringEventTemplate,
)


def _template() -> RecurringEventTemplate:
    return RecurringEventTemplate(
        id=uuid.uuid4(),
        district_id=uuid.uuid4(),
        title="Chor",
        category="Musik",
        start_time=time(19, 30),
        duration_minutes=90,
        recurrence=RecurrenceRule(
            kind=RecurrenceKind.WEEKLY,
            anchor_date=date(2026, 11, 3),
            weekdays=(2, 5),
            interval=2,
        ),
        excluded_dates=(date(2026, 11, 13),),
        revision=2,
    )


def test_template_roundtrips_versioned_rules_and_exclusions() -> None:
    original = _template()
    row = RecurringEventTemplateORM()
    _template_to_row(original, row)
    assert row.recurrence["kind"] == "WEEKLY"
    assert row.recurrence["anchor_date"] == "2026-11-03"
    assert row.excluded_dates == ["2026-11-13"]
    assert _template_from_row(row) == original


def test_decision_roundtrip_preserves_missing_slot_for_review() -> None:
    original = _template()
    row = RecurringEventDecisionORM(
        id=uuid.uuid4(),
        district_id=original.district_id,
        template_id=original.id,
        occurrence_local_date=date(2026, 11, 3),
        status="ACCEPTED",
        planning_slot_id=None,
        created_by="user",
    )
    assert _decision_from_row(row) == RecurringEventDecision(
        id=row.id,
        district_id=original.district_id,
        template_id=original.id,
        occurrence_local_date=row.occurrence_local_date,
        status=DecisionStatus.ACCEPTED,
        created_by="user",
        planning_slot_id=None,
    )


@pytest.mark.asyncio
async def test_new_template_is_flushed_for_transactional_persistence() -> None:
    session = AsyncMock()
    session.add = Mock()
    session.get.return_value = None
    template = _template()
    await SqlRecurringEventRepository(session).save_template(template)
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    saved = session.add.call_args.args[0]
    assert _template_from_row(saved) == template


@pytest.mark.asyncio
async def test_skipped_decision_is_removed_only_by_explicit_reopen() -> None:
    session = AsyncMock()
    session.get.return_value = None
    decision = RecurringEventDecision(
        id=uuid.uuid4(),
        district_id=uuid.uuid4(),
        template_id=uuid.uuid4(),
        occurrence_local_date=date(2026, 11, 24),
        status=DecisionStatus.SKIPPED,
        created_by="user",
    )
    repo = SqlRecurringEventRepository(session)
    await repo.save_decision(decision)
    session.flush.assert_awaited()
    assert session.add.call_count == 1
