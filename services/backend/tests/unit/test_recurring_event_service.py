# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Month projection and non-destructive recurring-event acceptance tests."""

from __future__ import annotations

import uuid
from datetime import date, time, timedelta
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


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["accept", "skip", "resolve_missing_slot"])
@pytest.mark.parametrize("translate_integrity_error", [False, True])
async def test_transaction_failure_translation_preserves_unrelated_errors(
    command: str, translate_integrity_error: bool,
) -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)

    class DatabaseIntegrityError(Exception):
        """Injected database constraint failure."""

    failure = DatabaseIntegrityError("constraint") if translate_integrity_error else RuntimeError("unavailable")
    service.integrity_error_type = DatabaseIntegrityError
    service.session.begin_nested.return_value.__aenter__.side_effect = failure
    kwargs = {"expected_revision": entry.revision}
    if command == "resolve_missing_slot":
        kwargs["action"] = "MARK_SKIPPED"
    else:
        kwargs["created_by"] = "u"

    expected_error = OccurrenceConflictError if translate_integrity_error else RuntimeError
    with pytest.raises(expected_error) as raised:
        await getattr(service, command)(entry, date(2026, 11, 3), **kwargs)

    if translate_integrity_error:
        assert raised.value.__cause__ is failure
    else:
        assert raised.value is failure
    repo.save_decision.assert_not_awaited()
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_unconfigured_integrity_error_is_propagated() -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)
    failure = RuntimeError("transaction unavailable")
    service.session.begin_nested.return_value.__aenter__.side_effect = failure

    with pytest.raises(RuntimeError) as raised:
        await service.accept(
            entry, date(2026, 11, 3), expected_revision=entry.revision, created_by="u",
        )

    assert raised.value is failure
    repo.save_decision.assert_not_awaited()
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_creates_public_instance_and_is_idempotent() -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)
    decision = await service.accept(
        entry, date(2026, 11, 3), expected_revision=entry.revision, created_by="u",
    )
    slot = slots.save.call_args.args[0]
    instance = instances.save.call_args.args[0]
    assert decision.planning_slot_id == slot.id
    assert slot.applicability == list(entry.applicability)
    assert slot.planning_date == date(2026, 11, 3)
    assert slot.planning_time == time(18, 30)
    assert instance.planning_slot_id == slot.id
    assert instance.actual_end_at - instance.actual_start_at == timedelta(minutes=90)
    repo.get_decision.return_value = decision
    slots.get.return_value = slot
    repeated = await service.accept(
        entry, date(2026, 11, 3), expected_revision=entry.revision, created_by="u",
    )
    assert repeated is decision
    slots.save.assert_awaited_once()
    instances.save.assert_awaited_once()
    repo.save_decision.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_input", [{"title_override": " "}, {"duration_minutes_override": 0}])
async def test_accept_rejects_invalid_overrides_without_writes(invalid_input: dict) -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)
    with pytest.raises(ValueError):
        await service.accept(
            entry, date(2026, 11, 3), expected_revision=entry.revision,
            created_by="u", **invalid_input,
        )
    repo.save_decision.assert_not_awaited()
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_template", [True, False])
async def test_accept_rejects_missing_template_or_nonoccurrence(missing_template: bool) -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)
    if missing_template:
        repo.get_template.return_value = None
    with pytest.raises(ValueError):
        await service.accept(
            entry, date(2026, 11, 4), expected_revision=entry.revision, created_by="u",
        )
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()
    repo.save_decision.assert_not_awaited()


@pytest.mark.asyncio
async def test_reopen_removes_only_skipped_decision() -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)
    decision = await service.skip(
        entry, date(2026, 11, 3), expected_revision=entry.revision, created_by="u",
    )
    repo.get_decision.return_value = decision
    await service.reopen(entry, date(2026, 11, 3), expected_revision=entry.revision)
    repo.delete_decision.assert_awaited_once_with(decision.id)
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_reopen_rejects_missing_decision() -> None:
    entry = _template()
    service, repo, _, _ = _service(entry)
    with pytest.raises(OccurrenceConflictError):
        await service.reopen(entry, date(2026, 11, 3), expected_revision=entry.revision)
    repo.delete_decision.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["MARK_SKIPPED", "REOPEN", "LINK_EXISTING"])
async def test_resolve_missing_slot_applies_explicit_action(action: str) -> None:
    entry = _template(congregation_id=uuid.uuid4())
    service, repo, slots, instances = _service(entry)
    decision = RecurringEventDecision(
        id=uuid.uuid4(), district_id=entry.district_id, template_id=entry.id,
        occurrence_local_date=date(2026, 11, 3), status=DecisionStatus.ACCEPTED,
        planning_slot_id=None, created_by="u",
    )
    repo.get_decision.return_value = decision
    repo.find_slot_decision.return_value = None
    target = PlanningSlot.create(
        district_id=entry.district_id, congregation_id=entry.congregation_id,
        title=entry.title, category=entry.category, planning_date=date(2026, 11, 3),
        planning_time=time(18, 30), approval_status=EventApprovalStatus.PLANNED,
    )
    slots.get.return_value = target
    result = await service.resolve_missing_slot(
        entry, date(2026, 11, 3), expected_revision=entry.revision,
        action=action, slot_id=target.id if action == "LINK_EXISTING" else None,
    )
    if action == "REOPEN":
        assert result is None
        repo.delete_decision.assert_awaited_once_with(decision.id)
        repo.save_decision.assert_not_awaited()
    else:
        assert result.id == decision.id
        assert result.status is (DecisionStatus.SKIPPED if action == "MARK_SKIPPED" else DecisionStatus.ACCEPTED)
        assert result.planning_slot_id == (target.id if action == "LINK_EXISTING" else None)
        repo.save_decision.assert_awaited_once_with(result)
        repo.delete_decision.assert_not_awaited()
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_rejects_missing_decision_without_writes() -> None:
    entry = _template()
    service, repo, slots, instances = _service(entry)
    with pytest.raises(OccurrenceConflictError):
        await service.resolve_missing_slot(
            entry, date(2026, 11, 3), expected_revision=entry.revision,
            action="MARK_SKIPPED",
        )
    repo.delete_decision.assert_not_awaited()
    repo.save_decision.assert_not_awaited()
    slots.save.assert_not_awaited()
    instances.save.assert_not_awaited()
