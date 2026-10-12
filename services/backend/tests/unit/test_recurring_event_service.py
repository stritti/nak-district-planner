# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Month projection and non-destructive recurring-event acceptance tests."""

from __future__ import annotations

import uuid
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.recurring_event_service import (
    OccurrenceConflictError,
    RecurringEventService,
    StaleTemplateError,
)
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlot
from app.domain.models.recurring_event_template import (
    ChecklistStatus,
    DecisionStatus,
    RecurrenceKind,
    RecurrenceRule,
    RecurringEventDecision,
    RecurringEventTemplate,
)


def _template(*, congregation_id: uuid.UUID | None = None) -> RecurringEventTemplate:
    return RecurringEventTemplate(
        id=uuid.uuid4(),
        district_id=uuid.uuid4(),
        congregation_id=congregation_id,
        title="Probe",
        category="Musik",
        start_time=time(19, 30),
        duration_minutes=90,
        recurrence=RecurrenceRule(
            kind=RecurrenceKind.WEEKLY,
            anchor_date=date(2026, 11, 3),
            weekdays=(2,),
        ),
    )


def _service(entry: RecurringEventTemplate) -> tuple[RecurringEventService, AsyncMock, AsyncMock, AsyncMock]:
    repo, slots, instances = AsyncMock(), AsyncMock(), AsyncMock()
    repo.list_decisions.return_value = []
    repo.list_templates.return_value = [entry]
    repo.get_template.return_value = entry
    repo.get_decision.return_value = None
    slots.list_for_date_range.return_value = []
    session = MagicMock()
    session.begin_nested.return_value = AsyncMock()
    return RecurringEventService(session, repo, slots, instances), repo, slots, instances


@pytest.mark.asyncio
async def test_month_projection_is_read_only_and_lists_tuesdays() -> None:
    entry = _template(congregation_id=uuid.uuid4())
    service, repo, slots, instances = _service(entry)
    result = await service.list_month(
        entry.district_id, 2026, 11, templates=[entry]
    )
    assert result.total == 4
    assert {row.status for row in result.items} == {ChecklistStatus.OPEN}
    assert [row.occurrence_local_date.day for row in result.items] == [3, 10, 17, 24]
    repo.save_decision.assert_not_awaited()
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_month_projection_preserves_skipped_decisions() -> None:
    entry = _template()
    service, repo, _, _ = _service(entry)
    repo.list_decisions.return_value = [
        RecurringEventDecision(
            id=uuid.uuid4(),
            district_id=entry.district_id,
            template_id=entry.id,
            occurrence_local_date=date(2026, 11, 10),
            status=DecisionStatus.SKIPPED,
            created_by="u",
        )
    ]
    result = await service.list_month(
        entry.district_id, 2026, 11, templates=[entry], status_filter=ChecklistStatus.SKIPPED
    )
    assert result.total == 1
    assert result.items[0].occurrence_local_date == date(2026, 11, 10)


@pytest.mark.asyncio
async def test_stale_preview_does_not_write_slot_or_decision() -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)
    with pytest.raises(StaleTemplateError):
        await service.accept(
            entry, date(2026, 11, 3), expected_revision=entry.revision + 1,
            created_by="u"
        )
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()
    repo.save_decision.assert_not_awaited()


@pytest.mark.asyncio
async def test_occupied_congregation_time_does_not_create_second_slot() -> None:
    congregation_id = uuid.uuid4()
    entry = _template(congregation_id=congregation_id)
    service, repo, slots, instances = _service(entry)
    existing = PlanningSlot.create(
        district_id=entry.district_id,
        congregation_id=congregation_id,
        title="Manuell",
        planning_date=date(2026, 11, 3),
        planning_time=time(18, 30),
        approval_status=EventApprovalStatus.PLANNED,
    )
    slots.list_for_date_range.return_value = [existing]
    with pytest.raises(OccurrenceConflictError):
        await service.accept(
            entry, date(2026, 11, 3), expected_revision=entry.revision, created_by="u"
        )
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()
    repo.save_decision.assert_not_awaited()


@pytest.mark.asyncio
async def test_skip_is_idempotent_and_creates_no_planning_slot() -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)
    decision = await service.skip(
        entry, date(2026, 11, 3), expected_revision=entry.revision, created_by="u"
    )
    assert decision.status == DecisionStatus.SKIPPED
    repo.save_decision.assert_awaited_once()
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()
    repo.get_decision.return_value = decision
    second = await service.skip(
        entry, date(2026, 11, 3), expected_revision=entry.revision, created_by="u"
    )
    assert second.id == decision.id
    repo.save_decision.assert_awaited_once()
