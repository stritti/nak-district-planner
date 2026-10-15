# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace as Namespace

import pytest
from pydantic import ValidationError

from app.adapters.api.schemas.export_token import ExportTokenCreate
from app.domain.models.export_token import ExportToken, TokenType
from app.domain.models.planning_slot import PlanningSlotStatus


def test_subject_token_is_internal_only():
    with pytest.raises(ValidationError):
        ExportTokenCreate(
            label="private", token_type="PUBLIC", district_id=uuid.uuid4(), subject_sub="alice"
        )


def test_subject_token_rejects_other_identity_filters():
    with pytest.raises(ValidationError):
        ExportTokenCreate(
            label="private",
            token_type="INTERNAL",
            district_id=uuid.uuid4(),
            subject_sub="alice",
            leader_id=uuid.uuid4(),
        )


def test_domain_subject_binding():
    token = ExportToken.create(
        "private", TokenType.INTERNAL, uuid.uuid4(), None, subject_sub="alice"
    )
    assert token.subject_sub == "alice"


def test_projection_merges_only_subject_scoped_duties_with_leader():
    from app.application.personal_calendar import project_personal_events

    district, congregation, slot_id, leader_id = [uuid.uuid4() for _ in range(4)]
    now = datetime(2026, 10, 13, tzinfo=UTC)
    slot = Namespace(
        id=slot_id,
        district_id=district,
        congregation_id=congregation,
        planning_date=date(2026, 10, 13),
        planning_time=None,
        title="Service",
        status=PlanningSlotStatus.CANCELLED,
        updated_at=now,
    )
    duty = {
        "planning_slot_id": slot_id,
        "district_id": district,
        "congregation_id": congregation,
        "linked_user_sub": "alice",
        "duty_label": "Organist",
        "updated_at": now,
    }
    duties = [
        Namespace(**duty),
        Namespace(**{**duty, "linked_user_sub": "bob", "duty_label": "SECRET"}),
        Namespace(**{**duty, "congregation_id": uuid.uuid4(), "duty_label": "QUARANTINED"}),
    ]
    events = project_personal_events(
        "alice",
        district,
        [slot],
        [],
        [Namespace(id=leader_id, user_sub="alice", district_id=district)],
        [Namespace(planning_slot_id=slot_id, event_id=slot_id, leader_id=leader_id)],
        duties,
    )
    assert len(events) == 1
    assert events[0].duties == ["Dienstleiter", "Organist"]
    assert events[0].status == "CANCELLED"
    assert events[0].uid == f"{slot_id}@nak-bezirksplaner"
    assert events[0].end_at > events[0].start_at


def test_personal_scope_requires_current_membership():
    from app.adapters.api.routers.personal_calendar import allowed_personal_scopes

    district, congregation = uuid.uuid4(), uuid.uuid4()
    auth = Namespace(user=Namespace(is_superadmin=False), memberships=[])
    assert allowed_personal_scopes(auth, district, {congregation}) == (False, set())
    auth.memberships = [Namespace(scope_type="CONGREGATION", scope_id=congregation, role="VIEWER")]
    assert allowed_personal_scopes(auth, district, {congregation}) == (False, {congregation})
    auth.memberships = [Namespace(scope_type="DISTRICT", scope_id=uuid.uuid4(), role="VIEWER")]
    assert allowed_personal_scopes(auth, district, {congregation}) == (False, set())


@pytest.mark.asyncio
async def test_owner_can_issue_subject_token(monkeypatch):
    from unittest.mock import AsyncMock

    from app.adapters.api.routers import export

    district = uuid.uuid4()
    auth = Namespace(user_sub="alice", user=Namespace(is_superadmin=False), memberships=[])
    monkeypatch.setattr(
        export, "personal_subject_context", AsyncMock(return_value=(True, set())), raising=False
    )
    repo = Namespace(save=AsyncMock())
    body = ExportTokenCreate(
        label="mine", token_type="INTERNAL", district_id=district, subject_sub="alice"
    )
    result = await export.create_export_token(auth, body, Namespace(), repo)
    assert result.subject_sub == "alice"


@pytest.mark.asyncio
async def test_other_subject_cannot_issue_token():
    from unittest.mock import AsyncMock

    from fastapi import HTTPException

    from app.adapters.api.routers import export

    auth = Namespace(user_sub="bob", user=Namespace(is_superadmin=False), memberships=[])
    with pytest.raises(HTTPException) as caught:
        await export.create_export_token(
            auth,
            ExportTokenCreate(
                label="mine", token_type="INTERNAL", district_id=uuid.uuid4(), subject_sub="alice"
            ),
            Namespace(),
            Namespace(save=AsyncMock()),
        )
    assert caught.value.status_code == 403


def test_projection_uses_instance_timing_and_ignores_name_only():
    from app.application.personal_calendar import project_personal_events

    district, slot_id = uuid.uuid4(), uuid.uuid4()
    now = datetime(2026, 10, 13, tzinfo=UTC)
    slot = Namespace(
        id=slot_id,
        district_id=district,
        congregation_id=None,
        planning_date=now.date(),
        planning_time=None,
        title="Old",
        status="ACTIVE",
        approval_status="PLANNED",
        updated_at=now,
    )
    instance = Namespace(
        planning_slot_id=slot_id,
        title="Actual",
        actual_start_at=now,
        actual_end_at=now,
        updated_at=now,
    )
    duty = Namespace(
        planning_slot_id=slot_id,
        district_id=district,
        congregation_id=None,
        linked_user_sub=None,
        duty_label="Secret",
        updated_at=now,
    )
    assert project_personal_events("alice", district, [slot], [instance], [], [], [duty]) == []
    duty.linked_user_sub = "alice"
    event = project_personal_events("alice", district, [slot], [instance], [], [], [duty])[0]
    assert event.title == "Actual"
    assert event.start_at == instance.actual_start_at
    assert event.status == "TENTATIVE"


def test_subject_ics_contains_one_uid_and_no_other_names():
    from app.adapters.api.routers.export import _personal_ics_response
    from app.application.personal_calendar import PersonalCalendarEvent

    now = datetime(2026, 10, 13, tzinfo=UTC)
    slot_id = uuid.uuid4()
    event = PersonalCalendarEvent(
        slot_id,
        f"{slot_id}@nak-bezirksplaner",
        "Service",
        now,
        now,
        "TENTATIVE",
        ["Organist"],
        None,
        now,
    )
    body = _personal_ics_response("Mine", [event]).body.decode()
    assert body.count("BEGIN:VEVENT") == 1
    assert "STATUS:TENTATIVE" in body
    assert "Organist" in body


@pytest.mark.asyncio
async def test_revoked_or_unknown_subject_feed_fails_closed():
    from unittest.mock import AsyncMock, Mock

    from fastapi import HTTPException

    from app.adapters.api.routers.personal_calendar import personal_subject_context

    session = Namespace(
        execute=AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))
    )
    with pytest.raises(HTTPException) as caught:
        await personal_subject_context(session, "missing", uuid.uuid4())
    assert caught.value.status_code == 404


@pytest.mark.asyncio
async def test_owner_token_listing_filters_other_subjects(monkeypatch):
    from unittest.mock import AsyncMock

    from app.adapters.api.routers import export

    district = uuid.uuid4()
    auth = Namespace(user_sub="alice", user=Namespace(is_superadmin=False), memberships=[])
    alice = ExportToken.create("a", TokenType.INTERNAL, district, None, subject_sub="alice")
    bob = ExportToken.create("b", TokenType.INTERNAL, district, None, subject_sub="bob")
    monkeypatch.setattr(export, "personal_subject_context", AsyncMock(return_value=(True, set())))
    result = await export.list_export_tokens(
        auth,
        Namespace(),
        district,
        Namespace(list_by_district=AsyncMock(return_value=[alice, bob])),
    )
    assert [token.subject_sub for token in result] == ["alice"]


@pytest.mark.asyncio
async def test_owner_revokes_subject_token(monkeypatch):
    from unittest.mock import AsyncMock

    from app.adapters.api.routers import export

    token = ExportToken.create("a", TokenType.INTERNAL, uuid.uuid4(), None, subject_sub="alice")
    auth = Namespace(user_sub="alice", user=Namespace(is_superadmin=False), memberships=[])
    monkeypatch.setattr(export, "personal_subject_context", AsyncMock(return_value=(True, set())))
    repo = Namespace(get=AsyncMock(return_value=token), delete=AsyncMock())
    await export.delete_export_token(auth, token.id, Namespace(), repo)
    repo.delete.assert_awaited_once_with(token.id)


@pytest.mark.asyncio
async def test_loader_filters_current_congregation_membership(monkeypatch):
    from unittest.mock import AsyncMock

    from app.adapters.api.routers import personal_calendar as router
    from app.adapters.db.repositories import event_duties

    district, own, foreign, slot_id = [uuid.uuid4() for _ in range(4)]
    now = datetime(2026, 10, 13, tzinfo=UTC)
    slot = Namespace(
        id=slot_id,
        district_id=district,
        congregation_id=own,
        planning_date=now.date(),
        planning_time=None,
        title="Mine",
        status="ACTIVE",
        updated_at=now,
    )
    other = Namespace(id=uuid.uuid4(), congregation_id=foreign)
    monkeypatch.setattr(router, "personal_subject_context", AsyncMock(return_value=(False, {own})))
    monkeypatch.setattr(
        router,
        "SqlPlanningSlotRepository",
        lambda session: Namespace(list_for_date_range=AsyncMock(return_value=[slot, other])),
    )
    monkeypatch.setattr(
        router,
        "SqlEventInstanceRepository",
        lambda session: Namespace(list_by_planning_slots=AsyncMock(return_value=[])),
    )
    monkeypatch.setattr(
        router,
        "SqlServiceAssignmentRepository",
        lambda session: Namespace(list_by_planning_slots=AsyncMock(return_value=[])),
    )
    monkeypatch.setattr(
        router,
        "SqlLeaderRepository",
        lambda session: Namespace(list_by_district=AsyncMock(return_value=[])),
    )
    duty = Namespace(
        planning_slot_id=slot_id,
        district_id=district,
        congregation_id=own,
        linked_user_sub="alice",
        duty_label="Organist",
        updated_at=now,
    )
    monkeypatch.setattr(
        event_duties,
        "SqlEventDutiesRepository",
        lambda session: Namespace(list_assignments=AsyncMock(return_value=[duty])),
    )
    result = await router.load_personal_events(
        Namespace(), "alice", district, now.date(), now.date()
    )
    assert [event.planning_slot_id for event in result] == [slot_id]


@pytest.mark.asyncio
async def test_personal_endpoint_rejects_invalid_date_range():
    from fastapi import HTTPException

    from app.adapters.api.routers.personal_calendar import personal_events

    with pytest.raises(HTTPException) as caught:
        await personal_events(
            Namespace(user_sub="alice"),
            Namespace(),
            uuid.uuid4(),
            date(2026, 10, 14),
            date(2026, 10, 13),
        )
    assert caught.value.status_code == 422


@pytest.mark.asyncio
async def test_existing_subject_revoked_membership_fails_closed(monkeypatch):
    from unittest.mock import AsyncMock, Mock

    from fastapi import HTTPException

    from app.adapters.api.routers import personal_calendar as router

    user = Namespace(is_superadmin=False)
    session = Namespace(
        execute=AsyncMock(
            side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=user)),
                Mock(scalars=Mock(return_value=[])),
            ]
        )
    )
    monkeypatch.setattr(
        router,
        "SqlMembershipRepository",
        lambda session: Namespace(get_all_by_user=AsyncMock(return_value=[])),
    )
    with pytest.raises(HTTPException) as caught:
        await router.personal_subject_context(session, "alice", uuid.uuid4())
    assert caught.value.status_code == 404


def test_unknown_role_does_not_authorize_personal_scope():
    from app.adapters.api.routers.personal_calendar import allowed_personal_scopes

    district = uuid.uuid4()
    auth = Namespace(
        user=Namespace(is_superadmin=False),
        memberships=[Namespace(scope_type="DISTRICT", scope_id=district, role="INVALID")],
    )
    assert allowed_personal_scopes(auth, district, set()) == (False, set())
