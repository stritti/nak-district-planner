# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""API-side RBAC, input validation and partial-bulk failure isolation."""

from __future__ import annotations

import uuid
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
from app.application.recurring_event_service import OccurrenceConflictError
from app.domain.models.membership import Membership, ScopeType
from app.domain.models.recurring_event_template import (
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
    entry = __import__("dataclasses").replace(entry, applicability=(str(other),))
    user = _auth(Role.VIEWER, ScopeType.CONGREGATION, own)
    assert not r._visible(user, entry)
    allowed = __import__("dataclasses").replace(entry, applicability=("all",))
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
        status=__import__(
            "app.domain.models.recurring_event_template", fromlist=["DecisionStatus"]
        ).DecisionStatus.ACCEPTED,
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
    assert result.results[0].error == "belegt"
    assert result.results[1].planning_slot_id == expected.planning_slot_id
    assert service.accept.await_count == 2


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
