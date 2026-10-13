# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""API-side RBAC, input validation and partial-bulk failure isolation."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.adapters.api.routers import recurring_events as r
from app.adapters.api.schemas.recurring_events import (
    BulkOccurrenceAcceptRequest,
    OccurrenceAcceptRequest,
    OccurrenceResolveRequest,
    RecurrenceRulePayload,
    RecurringTemplateCreate,
)
from app.application.recurring_event_service import (
    InvalidOccurrenceError,
    OccurrenceConflictError,
    StaleTemplateError,
)
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.recurring_event_template import (
    AmbiguousLocalTimeError,
    DecisionStatus,
    NonexistentLocalTimeError,
    RecurrenceKind,
    RecurrenceRule,
    RecurringEventTemplate,
)
from app.domain.models.role import Role


def _auth(
    role: Role,
    scope_type: ScopeType,
    scope_id: uuid.UUID,
    *,
    superadmin: bool = False,
):
    return SimpleNamespace(
        user=SimpleNamespace(is_superadmin=superadmin),
        user_sub="user",
        memberships=[
            Membership.create(
                user_sub="user", role=role, scope_type=scope_type, scope_id=scope_id,
            )
        ],
    )


def _template(congregation_id: uuid.UUID | None = None) -> RecurringEventTemplate:
    return RecurringEventTemplate(
        id=uuid.uuid4(),
        district_id=uuid.uuid4(),
        congregation_id=congregation_id,
        title="Chorprobe",
        category="Musik",
        start_time=time(19, 30),
        duration_minutes=90,
        recurrence=RecurrenceRule(
            kind=RecurrenceKind.WEEKLY,
            anchor_date=date(2026, 11, 3),
            weekdays=(2,),
        ),
    )


def _action(entry: RecurringEventTemplate) -> OccurrenceAcceptRequest:
    return OccurrenceAcceptRequest(
        template_id=entry.id,
        occurrence_local_date=date(2026, 11, 3),
        template_revision=entry.revision,
    )


@pytest.mark.parametrize("role", [Role.VIEWER, Role.PLANNER, Role.CONGREGATION_ADMIN])
def test_district_template_write_requires_district_admin(role: Role) -> None:
    entry = _template()
    with pytest.raises(HTTPException) as exc:
        r._require_write(
            _auth(role, ScopeType.DISTRICT, entry.district_id),
            entry.district_id, None,
        )
    assert exc.value.status_code == 403


def test_congregation_admin_can_only_write_own_scope() -> None:
    entry = _template(congregation_id=uuid.uuid4())
    user = _auth(Role.CONGREGATION_ADMIN, ScopeType.CONGREGATION, entry.congregation_id)
    r._require_write(user, entry.district_id, entry.congregation_id)
    with pytest.raises(HTTPException) as error:
        r._require_write(user, entry.district_id, uuid.uuid4())
    assert error.value.status_code == 403
    with pytest.raises(HTTPException):
        r._require_write(user, entry.district_id, None)


def test_district_admin_can_manage_district_and_congregation() -> None:
    entry = _template()
    user = _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, entry.district_id)
    r._require_write(user, entry.district_id, None)
    r._require_write(user, entry.district_id, uuid.uuid4())


def test_district_applicability_not_visible_to_uninvited_congregation() -> None:
    own = uuid.uuid4()
    other = uuid.uuid4()
    entry = _template()
    entry = replace(entry, applicability=(str(other),))
    user = _auth(Role.VIEWER, ScopeType.CONGREGATION, own)
    assert not r._visible(user, entry)
    allowed = replace(entry, applicability=("all",))
    assert r._visible(user, allowed)


def test_outgoing_template_schema_roundtrips_domain_rule() -> None:
    entry = _template()
    result = r._response(entry)
    assert result.recurrence.kind is RecurrenceKind.WEEKLY
    assert result.recurrence.anchor_date == date(2026, 11, 3)
    assert result.revision == 1


@pytest.mark.parametrize(
    "rule_data",
    [
        {"kind": "WEEKLY", "anchor_date": "2026-11-03", "weekdays": []},
        {"kind": "MONTHLY_DAY", "anchor_date": "2026-11-01", "day_of_month": 32},
        {"kind": "YEARLY", "anchor_date": "2026-11-01"},
    ],
)
def test_rule_schema_rejects_invalid_recurrence(rule_data: dict) -> None:
    with pytest.raises(ValidationError):
        RecurrenceRulePayload.model_validate(rule_data)


def test_create_schema_forbids_unknown_fields_and_service_template() -> None:
    body = {
        "title": "Chor", "category": "Musik", "start_time": "19:30",
        "duration_minutes": 90, "recurrence": {
            "kind": "WEEKLY", "anchor_date": "2026-11-03", "weekdays": [2]
        },
    }
    assert RecurringTemplateCreate.model_validate(body).category == "Musik"
    with pytest.raises(ValidationError):
        RecurringTemplateCreate.model_validate({**body, "unused": "bad"})


def test_resolve_schema_requires_slot_only_for_existing_link() -> None:
    entry = _template()
    request = {
        "template_id": entry.id,
        "occurrence_local_date": date(2026, 11, 3),
        "template_revision": 1,
    }
    with pytest.raises(ValidationError):
        OccurrenceResolveRequest.model_validate({**request, "action": "LINK_EXISTING"})
    with pytest.raises(ValidationError):
        OccurrenceResolveRequest.model_validate({
            **request, "action": "REOPEN", "planning_slot_id": uuid.uuid4()
        })


@pytest.mark.asyncio
async def test_bulk_partial_conflict_keeps_subsequent_successes() -> None:
    entry = _template()
    body = BulkOccurrenceAcceptRequest(items=[_action(entry), _action(entry)])
    expected = SimpleNamespace(
        status=DecisionStatus.ACCEPTED,
        planning_slot_id=uuid.uuid4(),
    )
    service = AsyncMock()
    service.accept.side_effect = [
        OccurrenceConflictError("belegt"), expected,
    ]
    with (
        patch.object(r, "_mutable_entry", AsyncMock(return_value=entry)),
        patch.object(r, "_service", return_value=service),
    ):
        result = await r.bulk_accept_recurring_occurrences(
            entry.district_id, body,
            _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, entry.district_id),
            AsyncMock(),
        )
    assert len(result.results) == 2
    assert result.results[0].error == "OCCURRENCE_CONFLICT"
    assert result.results[1].planning_slot_id == expected.planning_slot_id
    assert service.accept.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "expected_code"),
    [
        (StaleTemplateError("sensitive revision details"), "STALE_TEMPLATE"),
        (OccurrenceConflictError("sensitive slot details"), "OCCURRENCE_CONFLICT"),
        (InvalidOccurrenceError("sensitive template details"), "INVALID_OCCURRENCE"),
        (AmbiguousLocalTimeError("sensitive timing details"), "AMBIGUOUS_LOCAL_TIME"),
        (NonexistentLocalTimeError("sensitive timing details"), "NONEXISTENT_LOCAL_TIME"),
        (ValueError("internal sensitive details"), "INVALID_INPUT"),
    ],
)
async def test_bulk_errors_use_stable_codes_without_exposing_exception_text(
    failure: ValueError, expected_code: str,
) -> None:
    entry = _template()
    service = AsyncMock()
    service.accept.side_effect = failure
    with (
        patch.object(r, "_mutable_entry", AsyncMock(return_value=entry)),
        patch.object(r, "_service", return_value=service),
    ):
        response = await r.bulk_accept_recurring_occurrences(
            entry.district_id, BulkOccurrenceAcceptRequest(items=[_action(entry)]),
            _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, entry.district_id),
            AsyncMock(),
        )
    assert response.results[0].status is None
    assert response.results[0].error == expected_code
    assert "sensitive" not in response.model_dump_json()
    assert "internal" not in response.model_dump_json()


@pytest.mark.asyncio
async def test_create_fails_authorization_before_congregation_lookup() -> None:
    entry = _template(congregation_id=uuid.uuid4())
    payload = RecurringTemplateCreate(
        title=entry.title,
        category=entry.category,
        congregation_id=entry.congregation_id,
        start_time=entry.start_time,
        duration_minutes=90,
        recurrence=RecurrenceRulePayload(
            kind=RecurrenceKind.WEEKLY,
            anchor_date=date(2026, 11, 3), weekdays=(2,),
        ),
    )
    session = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await r.create_recurring_template(
            entry.district_id, payload,
            _auth(Role.VIEWER, ScopeType.CONGREGATION, entry.congregation_id),
            session,
        )
    assert exc.value.status_code == 403
    session.get.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["accept", "skip", "reopen", "resolve"])
@pytest.mark.parametrize("failure", [None, OccurrenceConflictError("changed"), ValueError("invalid")])
async def test_occurrence_routes_preserve_results_and_error_status(command: str, failure: Exception | None) -> None:
    entry = _template()
    user = _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, entry.district_id)
    service = AsyncMock()
    method = service.resolve_missing_slot if command == "resolve" else getattr(service, command)
    method.side_effect = failure
    method.return_value = SimpleNamespace(status=DecisionStatus.SKIPPED, planning_slot_id=None)
    body = _action(entry)
    if command == "resolve":
        body = OccurrenceResolveRequest(
            template_id=entry.id, occurrence_local_date=body.occurrence_local_date,
            template_revision=entry.revision, action="MARK_SKIPPED",
        )
    route = getattr(r, f"{command}_recurring_occurrence")
    with (
        patch.object(r, "_mutable_entry", AsyncMock(return_value=entry)),
        patch.object(r, "_service", return_value=service),
    ):
        if failure is not None:
            with pytest.raises(HTTPException) as error:
                await route(entry.district_id, body, user, AsyncMock())
            assert error.value.status_code == (409 if isinstance(failure, OccurrenceConflictError) else 422)
            assert error.value.__cause__ is failure
        else:
            result = await route(entry.district_id, body, user, AsyncMock())
            assert result.template_id == entry.id
            assert result.status.value == ("OPEN" if command == "reopen" else "SKIPPED")
    method.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign", [False, True])
async def test_mutable_entry_hides_missing_or_foreign_templates(foreign: bool) -> None:
    entry = _template()
    repo = AsyncMock()
    repo.get_template.return_value = entry if foreign else None
    with pytest.raises(HTTPException) as error:
        await r._mutable_entry(
            repo, uuid.uuid4(), entry.id,
            _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, entry.district_id),
        )
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_template_list_and_update_preserve_revision_contract() -> None:
    entry = _template()
    user = _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, entry.district_id)
    repo = AsyncMock()
    repo.list_templates.return_value = [entry]
    repo.get_template.return_value = entry
    with patch.object(r, "_repository", return_value=repo):
        listed = await r.list_recurring_templates(entry.district_id, user, AsyncMock())
        assert listed.total == 1
        assert listed.items[0].id == entry.id
        updated = await r.update_recurring_template(
            entry.district_id, entry.id,
            r.RecurringTemplatePatch(expected_revision=entry.revision, title="Updated"),
            user, AsyncMock(),
        )
        assert updated.title == "Updated"
        assert updated.revision == entry.revision + 1
        repo.save_template.assert_awaited_once()
        with pytest.raises(HTTPException) as error:
            await r.update_recurring_template(
                entry.district_id, entry.id,
                r.RecurringTemplatePatch(expected_revision=entry.revision + 1),
                user, AsyncMock(),
            )
        assert error.value.status_code == 409
        repo.save_template.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_template_persists_valid_district_template() -> None:
    entry = _template()
    repo = AsyncMock()
    payload = RecurringTemplateCreate(
        title=entry.title, category=entry.category, start_time=entry.start_time,
        duration_minutes=90, recurrence=RecurrenceRulePayload(
            kind=RecurrenceKind.WEEKLY, anchor_date=date(2026, 11, 3), weekdays=(2,),
        ),
    )
    with patch.object(r, "_repository", return_value=repo):
        result = await r.create_recurring_template(
            entry.district_id, payload,
            _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, entry.district_id),
            AsyncMock(),
        )
    assert result.title == entry.title
    assert result.district_id == entry.district_id
    repo.save_template.assert_awaited_once()


@pytest.mark.asyncio
async def test_checklist_passes_filters_and_pagination_to_service() -> None:
    entry = _template(congregation_id=uuid.uuid4())
    repo = AsyncMock()
    repo.list_templates.return_value = [entry]
    service = AsyncMock()
    service.list_month.return_value = SimpleNamespace(
        items=[], total=0, limit=5, offset=10, counts={"OPEN": 0},
    )
    with (
        patch.object(r, "_repository", return_value=repo),
        patch.object(r, "_service", return_value=service),
        patch.object(r, "_validate_congregation", AsyncMock()),
    ):
        result = await r.list_recurring_checklist(
            entry.district_id,
            _auth(Role.DISTRICT_ADMIN, ScopeType.DISTRICT, entry.district_id),
            AsyncMock(), year=2026, month=11, congregation_id=entry.congregation_id,
            q="choir", category="Musik", approval_status=r.ChecklistStatus.OPEN,
            limit=5, offset=10,
        )
    assert result.total == 0
    kwargs = service.list_month.call_args.kwargs
    assert kwargs["templates"] == [entry]
    assert kwargs["query"] == "choir"
    assert kwargs["category"] == "Musik"
    assert kwargs["status_filter"] is r.ChecklistStatus.OPEN
    assert kwargs["limit"] == 5
    assert kwargs["offset"] == 10


@pytest.mark.asyncio
async def test_congregation_and_distribution_reject_cross_district_ids() -> None:
    entry = _template()
    congregation_id = uuid.uuid4()
    congregations = AsyncMock()
    congregations.get.return_value = SimpleNamespace(id=congregation_id, district_id=uuid.uuid4())
    congregations.list_by_district.return_value = []
    with patch.object(r, "SqlCongregationRepository", return_value=congregations):
        with pytest.raises(HTTPException) as error:
            await r._validate_congregation(AsyncMock(), entry.district_id, congregation_id)
        assert error.value.status_code == 403
        with pytest.raises(HTTPException) as error:
            await r._validate_distribution(
                AsyncMock(), replace(entry, applicability=(str(congregation_id),)),
            )
        assert error.value.status_code == 403
