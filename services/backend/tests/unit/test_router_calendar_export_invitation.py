"""Tests for calendar-integration, export, and invitation routers.

Event-free architecture: uses PlanningSlot + EventInstance instead of Event.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.adapters.api.routers import calendar_integrations as ci_router
from app.adapters.api.routers import export as export_router
from app.adapters.api.routers import invitations as inv_router
from app.adapters.api.schemas.calendar_integration import (
    CalendarIntegrationCreate,
    CalendarIntegrationUpdate,
)
from app.adapters.api.schemas.export_token import ExportTokenCreate
from app.adapters.api.schemas.invitation import (
    InvitationCreate,
    InvitationTargetCreate,
    OverwriteDecisionRequest,
)
from app.application.sync_service import SyncResult as SyncServiceResult
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
)
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.export_token import ExportToken, TokenType
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationOverwriteRequest,
    InvitationTargetType,
    OverwriteDecisionStatus,
)
from app.domain.models.leader import Leader
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _auth_context(user_sub: str = "user1", is_superadmin: bool = False):
    """Build a minimal auth context duck-type for the routers."""
    user = type("U", (), {"is_superadmin": is_superadmin})()
    return type("A", (), {"memberships": [], "user_sub": user_sub, "user": user})()


def _integration(**overrides) -> CalendarIntegration:
    return CalendarIntegration.create(
        district_id=overrides.get("district_id", uuid.uuid4()),
        congregation_id=overrides.get("congregation_id"),
        name=overrides.get("name", "ICS"),
        type=overrides.get("type", CalendarType.ICS),
        credentials_enc=overrides.get("credentials_enc", "enc"),
        capabilities=overrides.get("capabilities", [CalendarCapability.READ]),
        sync_interval=overrides.get("sync_interval", 60),
    )


def _planning_slot(**overrides) -> PlanningSlot:
    return PlanningSlot.create(
        district_id=overrides.get("district_id", uuid.uuid4()),
        planning_date=overrides.get("planning_date", date(2026, 6, 15)),
        planning_time=overrides.get("planning_time", time(10, 0)),
        congregation_id=overrides.get("congregation_id", uuid.uuid4()),
        category=overrides.get("category", "Gottesdienst"),
        title=overrides.get("title", "Gottesdienst"),
        approval_status=overrides.get("approval_status", EventApprovalStatus.CONFIRMED),
        slot_id=overrides.get("slot_id"),
        status=overrides.get("status", PlanningSlotStatus.ACTIVE),
        applicability=overrides.get("applicability"),
    )


def _event_instance(planning_slot_id: uuid.UUID, **overrides) -> EventInstance:
    return EventInstance.create(
        planning_slot_id=planning_slot_id,
        title=overrides.get("title", "Gottesdienst"),
        actual_start_at=overrides.get(
            "actual_start_at", datetime(2026, 6, 15, 10, 0, tzinfo=UTC)
        ),
        actual_end_at=overrides.get(
            "actual_end_at", datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
        ),
        source=overrides.get("source", EventSource.INTERNAL),
        visibility=overrides.get("visibility", EventVisibility.PUBLIC),
        description=overrides.get("description"),
        instance_id=overrides.get("instance_id"),
    )


def _export_repos(
    *,
    token: ExportToken | None,
    slots: list | None = None,
    instances: list | None = None,
    assignments: list | None = None,
    leaders: list | None = None,
) -> dict:
    token_repo = AsyncMock()
    token_repo.get_by_token.return_value = token

    slot_repo = AsyncMock()
    slot_repo.list_for_date_range.return_value = slots or []

    instance_repo = AsyncMock()
    instance_repo.list_by_planning_slots.return_value = instances or []

    sa_repo = AsyncMock()
    sa_repo.list_by_planning_slots.return_value = assignments or []

    leader_repo = AsyncMock()
    leader_repo.list_by_district.return_value = leaders or []

    return {
        "token_repo": token_repo,
        "slot_repo": slot_repo,
        "instance_repo": instance_repo,
        "sa_repo": sa_repo,
        "leader_repo_dep": leader_repo,
    }


def _export_session(db: AsyncMock) -> AsyncMock:
    session_result = MagicMock()
    session_result.scalars.return_value = []
    db.execute.return_value = session_result
    return db


def _assignment_stub(
    slot_id: uuid.UUID, leader_name: str, leader_id: uuid.UUID | None = None
) -> object:
    return type(
        "SA",
        (),
        {
            "event_id": slot_id,
            "planning_slot_id": slot_id,
            "leader_id": leader_id,
            "leader_name": leader_name,
            "status": "ASSIGNED",
        },
    )()


# ===================================================================
# Calendar Integration tests  (unchanged logic, only import changes)
# ===================================================================


@pytest.mark.asyncio
async def test_calendar_integration_routes_success_and_errors() -> None:
    district_id = uuid.uuid4()
    integration = _integration(district_id=district_id)
    db = AsyncMock()
    auth = _auth_context()
    service = AsyncMock()
    service.create_integration.return_value = _integration(name="Name")
    service.update_integration.return_value = _integration(name="Neu")

    with (
        patch("app.adapters.api.routers.calendar_integrations.require_role_in_district"),
        patch(
            "app.adapters.api.routers.calendar_integrations.encrypt_credentials",
            return_value="enc",
        ),
        patch(
            "app.adapters.api.routers.calendar_integrations.run_sync",
            new=AsyncMock(
                return_value=SyncServiceResult(
                    created=1,
                    updated=2,
                    cancelled=3,
                    auto_matched=4,
                )
            ),
        ),
    ):
        repo = AsyncMock()
        repo.get.return_value = integration
        repo.list_by_district.return_value = [integration]
        repo.list_active.return_value = [integration]

        created = await ci_router.create_calendar_integration(
            CalendarIntegrationCreate(
                district_id=district_id,
                name="Name",
                type=CalendarType.ICS,
                credentials={"url": "https://calendar.example.com/feed.ics"},
            ),
            auth,
            db,
            service=service,
        )
        listed = await ci_router.list_calendar_integrations(
            auth, db, repo=repo, district_id=district_id
        )
        sync = await ci_router.trigger_sync(integration.id, auth, db, repo=repo)
        updated = await ci_router.update_calendar_integration(
            integration.id,
            CalendarIntegrationUpdate(name="Neu"),
            auth,
            db,
            repo=repo,
            service=service,
        )
        await ci_router.delete_calendar_integration(integration.id, auth, db, repo=repo)

    assert created.name == "Name"
    assert listed.total == 1
    assert sync.created == 1
    assert sync.auto_matched == 4
    assert updated.name == "Neu"


@pytest.mark.asyncio
async def test_calendar_integration_not_found_and_bad_sync() -> None:
    auth = _auth_context()
    repo = AsyncMock()
    repo.get.return_value = None
    with pytest.raises(HTTPException):
        await ci_router.trigger_sync(uuid.uuid4(), auth, AsyncMock(), repo=repo)
    with pytest.raises(HTTPException):
        await ci_router.update_calendar_integration(
            uuid.uuid4(),
            CalendarIntegrationUpdate(name="X"),
            auth,
            AsyncMock(),
            repo=repo,
        )
    with pytest.raises(HTTPException):
        await ci_router.delete_calendar_integration(uuid.uuid4(), auth, AsyncMock(), repo=repo)


@pytest.mark.asyncio
async def test_list_calendar_integrations_congregation_scoped() -> None:
    congregation_id = uuid.uuid4()
    district_id = uuid.uuid4()
    integration = _integration(
        district_id=district_id,
        congregation_id=congregation_id,
        name="Cong ICS",
    )
    db = AsyncMock()
    auth = _auth_context()

    with patch(
        "app.adapters.api.routers.calendar_integrations.assert_has_role_in_congregation"
    ):
        repo = AsyncMock()
        repo.list_by_congregation.return_value = [integration]

        listed = await ci_router.list_calendar_integrations(
            auth, db, repo=repo, congregation_id=congregation_id
        )

    assert listed.total == 1
    assert listed.items[0].congregation_id == congregation_id


@pytest.mark.asyncio
async def test_list_calendar_integrations_congregation_scoped_validates_district() -> None:
    congregation_id = uuid.uuid4()
    other_district_id = uuid.uuid4()
    db = AsyncMock()
    auth = _auth_context()

    with patch(
        "app.adapters.api.routers.calendar_integrations.assert_has_role_in_congregation"
    ):
        repo = AsyncMock()
        cong_repo = AsyncMock()
        # congregation belongs to a different district
        cong_repo.get.return_value = type("C", (), {"district_id": uuid.uuid4()})()

        with pytest.raises(HTTPException) as exc:
            await ci_router.list_calendar_integrations(
                auth,
                db,
                repo=repo,
                district_id=other_district_id,
                congregation_id=congregation_id,
                cong_repo=cong_repo,
            )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_calendar_integrations_congregation_scoped_forbidden() -> None:
    congregation_id = uuid.uuid4()
    db = AsyncMock()
    auth = _auth_context()

    with patch(
        "app.adapters.api.routers.calendar_integrations.assert_has_role_in_congregation",
        side_effect=ci_router.PermissionError("no permission"),
    ):
        repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await ci_router.list_calendar_integrations(
                auth, db, repo=repo, congregation_id=congregation_id
            )

    assert exc.value.status_code == 403


# ===================================================================
# Export token tests  (adapted for PlanningSlot + EventInstance)
# ===================================================================


@pytest.mark.asyncio
async def test_export_token_crud() -> None:
    """Create, list, and delete export tokens."""
    district_id = uuid.uuid4()
    auth = _auth_context(is_superadmin=False)
    token = ExportToken.create(
        label="L",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    db = AsyncMock()
    token_repo = AsyncMock()
    token_repo.get.return_value = token
    token_repo.get_by_token.return_value = token
    token_repo.list_by_district.return_value = [token]
    token_repo.delete.return_value = True
    with patch("app.adapters.api.routers.export.require_role_in_district"):
        created = await export_router.create_export_token(
            auth,
            ExportTokenCreate(
                label="X",
                token_type=TokenType.INTERNAL,
                district_id=district_id,
                congregation_id=None,
            ),
            db,
            repo=token_repo,
        )
        listed = await export_router.list_export_tokens(
            auth, db, district_id=district_id, repo=token_repo
        )
        await export_router.delete_export_token(auth, token.id, db, repo=token_repo)

    assert created.label == "X"
    assert len(listed) == 1
    assert listed[0].id == token.id


@pytest.mark.asyncio
async def test_export_token_management() -> None:
    """Create, list, and delete export tokens (management route)."""
    district_id = uuid.uuid4()
    auth = _auth_context(is_superadmin=False)
    token = ExportToken.create(
        label="L",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    db = AsyncMock()
    token_repo = AsyncMock()
    token_repo.get.return_value = token
    token_repo.get_by_token.return_value = token
    token_repo.list_by_district.return_value = [token]
    token_repo.delete.return_value = True
    with patch("app.adapters.api.routers.export.require_role_in_district"):
        created = await export_router.create_export_token(
            auth,
            ExportTokenCreate(
                label="X",
                token_type=TokenType.INTERNAL,
                district_id=district_id,
                congregation_id=None,
            ),
            db,
            repo=token_repo,
        )
        listed = await export_router.list_export_tokens(
            auth, db, district_id=district_id, repo=token_repo
        )
        await export_router.delete_export_token(auth, token.id, db, repo=token_repo)

    assert created.label == "X"
    assert len(listed) == 1
    assert listed[0].id == token.id


@pytest.mark.asyncio
async def test_export_calendar_ics_with_planning_slots() -> None:
    """ICS export produces a valid calendar with VEVENT entries from slots."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    instance = _event_instance(planning_slot_id=slot.id)

    token = ExportToken.create(
        label="Export",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    db = _export_session(AsyncMock())
    repos = _export_repos(token=token, slots=[slot], instances=[instance])

    response = await export_router.export_calendar_ics(
        token.token, db, approval_status=None, **repos
    )

    assert b"BEGIN:VCALENDAR" in response.body
    assert b"BEGIN:VEVENT" in response.body
    assert b"END:VEVENT" in response.body
    # UID uses the slot id
    assert str(slot.id).encode() in response.body
    # Title from EventInstance
    assert b"Gottesdienst" in response.body


@pytest.mark.asyncio
async def test_export_calendar_ics_filters_by_approval_status() -> None:
    """confirmed_only filter excludes PLANNED slots."""
    district_id = uuid.uuid4()
    confirmed_slot = _planning_slot(
        district_id=district_id,
        approval_status=EventApprovalStatus.CONFIRMED,
        slot_id=uuid.uuid4(),
    )
    planned_slot = _planning_slot(
        district_id=district_id,
        approval_status=EventApprovalStatus.PLANNED,
        title="Geplant",
        slot_id=uuid.uuid4(),
    )
    confirmed_instance = _event_instance(
        planning_slot_id=confirmed_slot.id,
        instance_id=uuid.uuid4(),
    )

    token = ExportToken.create(
        label="Export",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    db = _export_session(AsyncMock())
    repos = _export_repos(
        token=token,
        slots=[confirmed_slot, planned_slot],
        instances=[confirmed_instance],
    )

    response = await export_router.export_calendar_ics(
        token.token, db, approval_status="confirmed_only", **repos
    )

    # Only the confirmed slot should appear
    assert response.body.count(b"BEGIN:VEVENT") == 1
    assert str(confirmed_slot.id).encode() in response.body


@pytest.mark.asyncio
async def test_export_calendar_ics_leader_token_shows_assignments() -> None:
    """Leader-specific export includes congregation name and leader comment."""
    district_id = uuid.uuid4()
    leader_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    instance = _event_instance(planning_slot_id=slot.id)

    token = ExportToken.create(
        label="Leader Export",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
        leader_id=leader_id,
    )
    db = _export_session(AsyncMock())
    repos = _export_repos(
        token=token,
        slots=[slot],
        instances=[instance],
        assignments=[
            _assignment_stub(slot.id, "Bezirksvorsteher Müller", leader_id=leader_id)
        ],
    )

    response = await export_router.export_calendar_ics(
        token.token, db, approval_status=None, **repos
    )

    assert b"Dienstleiter: Bezirksvorsteher M" in response.body


@pytest.mark.asyncio
async def test_public_feed_anonymizes_leader_id_assignment_without_loading_leaders() -> None:
    """PUBLIC feeds never read leader rows (RLS denies them) yet still mark the slot as assigned."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    token = ExportToken.create(
        label="Public", token_type=TokenType.PUBLIC, district_id=district_id, congregation_id=None
    )
    repos = _export_repos(
        token=token, slots=[slot], assignments=[_assignment_stub(slot.id, "", leader_id=uuid.uuid4())]
    )

    response = await export_router.export_calendar_ics(
        token.token, _export_session(AsyncMock()), approval_status=None, **repos
    )

    assert b"Dienstleiter: [Name anonymisiert]" in response.body
    repos["leader_repo_dep"].list_by_district.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("token_type", "personal", "exported"),
    [("PUBLIC", False, False), ("PUBLIC", True, True), ("INTERNAL", False, True)],
)
async def test_internal_events_stay_out_of_public_feeds(token_type, personal, exported) -> None:
    """A PUBLIC feed must not leak title/description of INTERNAL-visibility events."""
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    slot = _planning_slot(
        district_id=district_id, congregation_id=None, applicability=[str(congregation_id)]
    )
    instance = _event_instance(planning_slot_id=slot.id, visibility=EventVisibility.INTERNAL)
    leader_id = uuid.uuid4() if personal else None
    token = ExportToken.create(
        label="Feed",
        token_type=TokenType(token_type),
        district_id=district_id,
        congregation_id=None if personal else congregation_id,
        leader_id=leader_id,
    )
    assignments = [_assignment_stub(slot.id, "Leiter", leader_id=leader_id)] if personal else []
    repos = _export_repos(token=token, slots=[slot], instances=[instance], assignments=assignments)

    response = await export_router.export_calendar_ics(
        token.token, _export_session(AsyncMock()), approval_status=None, **repos
    )

    assert (f"UID:{slot.id}@nak-bezirksplaner".encode() in response.body) is exported


@pytest.mark.asyncio
async def test_export_calendar_ics_empty() -> None:
    """Export with no slots produces valid calendar with no VEVENT."""
    district_id = uuid.uuid4()
    token = ExportToken.create(
        label="Empty",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    db = _export_session(AsyncMock())
    repos = _export_repos(token=token)

    response = await export_router.export_calendar_ics(
        token.token, db, approval_status=None, **repos
    )

    assert b"BEGIN:VCALENDAR" in response.body
    assert b"BEGIN:VEVENT" not in response.body


@pytest.mark.asyncio
async def test_export_token_not_found_paths() -> None:
    """Unknown tokens return 404 for ICS export and token deletion."""
    token_repo = AsyncMock()
    token_repo.get_by_token.return_value = None
    token_repo.get.return_value = None
    with pytest.raises(HTTPException):
        await export_router.export_calendar_ics(
            "missing",
            AsyncMock(),
            token_repo=token_repo,
            slot_repo=AsyncMock(),
            instance_repo=AsyncMock(),
            sa_repo=AsyncMock(),
            leader_repo_dep=AsyncMock(),
        )
    with pytest.raises(HTTPException):
        await export_router.delete_export_token(
            _auth_context(), uuid.uuid4(), AsyncMock(), repo=token_repo
        )


@pytest.mark.asyncio
async def test_export_token_write_routes_forbidden_without_permission() -> None:
    """Token write routes require DISTRICT_ADMIN."""
    district_id = uuid.uuid4()
    token = ExportToken.create(
        label="L",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    auth = _auth_context()
    token_repo = AsyncMock()
    token_repo.get.return_value = token
    with patch(
        "app.adapters.api.routers.export.require_role_in_district",
        side_effect=HTTPException(status_code=403, detail="forbidden"),
    ):
        with pytest.raises(HTTPException) as create_exc:
            await export_router.create_export_token(
                auth,
                ExportTokenCreate(
                    label="X",
                    token_type=TokenType.INTERNAL,
                    district_id=district_id,
                ),
                AsyncMock(),
                repo=token_repo,
            )
        with pytest.raises(HTTPException) as delete_exc:
            await export_router.delete_export_token(auth, token.id, AsyncMock(), repo=token_repo)

    assert create_exc.value.status_code == 403
    assert delete_exc.value.status_code == 403


@pytest.mark.asyncio
async def test_list_routes_require_district_id_for_non_superadmin() -> None:
    auth = _auth_context(is_superadmin=False)

    with pytest.raises(HTTPException) as ci_exc:
        await ci_router.list_calendar_integrations(
            auth, AsyncMock(), repo=AsyncMock(), district_id=None
        )
    with pytest.raises(HTTPException) as export_exc:
        await export_router.list_export_tokens(
            auth, AsyncMock(), district_id=None, repo=AsyncMock()
        )

    assert ci_exc.value.status_code == 403
    assert export_exc.value.status_code == 403


# ===================================================================
# Invitation tests  (adapted for PlanningSlot)
# ===================================================================


@pytest.mark.asyncio
async def test_invitation_routes_success_and_error_paths() -> None:
    district_id = uuid.uuid4()
    source_slot = _planning_slot(district_id=district_id)
    source_instance = _event_instance(planning_slot_id=source_slot.id)

    invitation = CongregationInvitation.create(
        source_event_id=source_slot.id,
        source_planning_slot_id=source_slot.id,
        source_congregation_id=source_slot.congregation_id or uuid.uuid4(),
        target_type=InvitationTargetType.EXTERNAL_NOTE,
        external_target_note="extern",
    )
    overwrite = InvitationOverwriteRequest.create(
        invitation_id=invitation.id,
        source_event_id=source_slot.id,
        target_event_id=source_slot.id,
        proposed_title="N",
        proposed_start_at=datetime.now(UTC),
        proposed_end_at=datetime.now(UTC) + timedelta(hours=1),
        proposed_description=None,
        proposed_category=None,
    )
    auth = _auth_context()
    db = AsyncMock()

    slot_repo = AsyncMock()
    slot_repo.get.return_value = source_slot

    inst_repo = AsyncMock()
    inst_repo.get_by_planning_slot.return_value = source_instance

    inv_repo = AsyncMock()
    inv_repo.get.return_value = invitation
    inv_repo.list_by_source_event.return_value = [invitation]

    req_repo = AsyncMock()
    req_repo.get.return_value = overwrite
    req_repo.list_open_by_district.return_value = [overwrite]

    with (
        patch("app.adapters.api.routers.invitations.require_role_in_district"),
        patch(
            "app.adapters.api.routers.invitations.create_invitations_for_event",
            new=AsyncMock(return_value=[invitation]),
        ),
        patch(
            "app.adapters.api.routers.invitations.delete_invitation",
            new=AsyncMock(return_value=True),
        ),
        patch(
            "app.adapters.api.routers.invitations.apply_overwrite_decision",
            new=AsyncMock(return_value=overwrite),
        ),
    ):
        created = await inv_router.create_invitations(
            source_slot.id,
            InvitationCreate(
                targets=[
                    InvitationTargetCreate(
                        target_type=InvitationTargetType.EXTERNAL_NOTE,
                        external_target_note="extern",
                    )
                ]
            ),
            auth,
            db,
            slot_repo=slot_repo,
        )
        listed = await inv_router.list_event_invitations(
            source_slot.id, auth, db, slot_repo=slot_repo, inv_repo=inv_repo
        )
        await inv_router.remove_invitation(
            invitation.id, auth, db, inv_repo=inv_repo, slot_repo=slot_repo
        )
        ovr = await inv_router.list_overwrite_requests(
            auth,
            db,
            district_id=district_id,
            req_repo=req_repo,
            slot_repo=slot_repo,
            instance_repo=inst_repo,
        )
        decided = await inv_router.decide_overwrite_request(
            overwrite.id,
            OverwriteDecisionRequest(decision=OverwriteDecisionStatus.ACCEPTED),
            auth,
            db,
            req_repo=req_repo,
            slot_repo=slot_repo,
            instance_repo=inst_repo,
        )

    assert created and listed and ovr
    assert decided.id == overwrite.id


@pytest.mark.asyncio
async def test_invitation_not_found_paths() -> None:
    auth = _auth_context()
    slot_id = uuid.uuid4()

    slot_repo = AsyncMock()
    slot_repo.get.return_value = None
    with pytest.raises(HTTPException):
        await inv_router.create_invitations(
            slot_id,
            InvitationCreate(
                targets=[
                    InvitationTargetCreate(
                        target_type=InvitationTargetType.EXTERNAL_NOTE,
                        external_target_note="x",
                    )
                ]
            ),
            auth,
            AsyncMock(),
            slot_repo=slot_repo,
        )

    inv_repo = AsyncMock()
    inv_repo.get.return_value = None
    with pytest.raises(HTTPException):
        await inv_router.remove_invitation(uuid.uuid4(), auth, AsyncMock(), inv_repo=inv_repo)

    req_repo = AsyncMock()
    req_repo.get.return_value = None
    with pytest.raises(HTTPException):
        await inv_router.decide_overwrite_request(
            uuid.uuid4(),
            OverwriteDecisionRequest(decision=OverwriteDecisionStatus.ACCEPTED),
            auth,
            AsyncMock(),
            req_repo=req_repo,
        )


@pytest.mark.asyncio
async def test_invitation_create_for_district_congregation() -> None:
    """Create an invitation targeting another congregation within the same district."""
    district_id = uuid.uuid4()
    source_cong_id = uuid.uuid4()
    target_cong_id = uuid.uuid4()
    source_slot = _planning_slot(
        district_id=district_id,
        congregation_id=source_cong_id,
    )
    source_instance = _event_instance(planning_slot_id=source_slot.id)

    invitation = CongregationInvitation.create(
        source_event_id=source_slot.id,
        source_planning_slot_id=source_slot.id,
        source_congregation_id=source_cong_id,
        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        target_congregation_id=target_cong_id,
        linked_event_id=uuid.uuid4(),
    )
    auth = _auth_context()
    db = AsyncMock()

    slot_repo = AsyncMock()
    slot_repo.get.return_value = source_slot

    inst_repo = AsyncMock()
    inst_repo.get_by_planning_slot.return_value = source_instance

    inv_repo = AsyncMock()
    inv_repo.list_by_source_event.return_value = [invitation]

    with (
        patch("app.adapters.api.routers.invitations.require_role_in_district"),
        patch(
            "app.adapters.api.routers.invitations.create_invitations_for_event",
            new=AsyncMock(return_value=[invitation]),
        ),
    ):
        created = await inv_router.create_invitations(
            source_slot.id,
            InvitationCreate(
                targets=[
                    InvitationTargetCreate(
                        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                        target_congregation_id=target_cong_id,
                    )
                ]
            ),
            auth,
            db,
            slot_repo=slot_repo,
        )

    assert len(created) == 1
    assert created[0].target_type == InvitationTargetType.DISTRICT_CONGREGATION
    assert created[0].target_congregation_id == target_cong_id


@pytest.mark.asyncio
async def test_invitation_remove_with_missing_planning_slot() -> None:
    """remove_invitation returns 404 when the invitation's source planning slot is gone."""
    district_id = uuid.uuid4()
    source_slot = _planning_slot(district_id=district_id)
    invitation = CongregationInvitation.create(
        source_event_id=source_slot.id,
        source_planning_slot_id=source_slot.id,
        source_congregation_id=source_slot.congregation_id or uuid.uuid4(),
        target_type=InvitationTargetType.EXTERNAL_NOTE,
        external_target_note="ext",
    )
    auth = _auth_context()
    db = AsyncMock()

    inv_repo = AsyncMock()
    inv_repo.get.return_value = invitation

    slot_repo = AsyncMock()
    slot_repo.get.return_value = None  # planning slot not found

    with pytest.raises(HTTPException) as exc:
        await inv_router.remove_invitation(
            invitation.id, auth, db, inv_repo=inv_repo, slot_repo=slot_repo
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_invitation_list_overwrite_requests() -> None:
    """List overwrite requests returns pending requests for a district."""
    district_id = uuid.uuid4()
    source_slot = _planning_slot(district_id=district_id)
    source_instance = _event_instance(planning_slot_id=source_slot.id)
    target_slot = _planning_slot(
        district_id=district_id,
        congregation_id=uuid.uuid4(),
        slot_id=uuid.uuid4(),
    )
    target_instance = _event_instance(
        planning_slot_id=target_slot.id,
        instance_id=uuid.uuid4(),
    )

    invitation = CongregationInvitation.create(
        source_event_id=source_slot.id,
        source_planning_slot_id=source_slot.id,
        source_congregation_id=source_slot.congregation_id or uuid.uuid4(),
        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        target_congregation_id=target_slot.congregation_id,
        linked_event_id=target_slot.id,
    )
    overwrite = InvitationOverwriteRequest.create(
        invitation_id=invitation.id,
        source_event_id=source_slot.id,
        target_event_id=target_slot.id,
        proposed_title="Updated Title",
        proposed_start_at=datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        proposed_end_at=datetime(2026, 6, 15, 12, 0, tzinfo=UTC),
        proposed_description=None,
        proposed_category=None,
    )
    auth = _auth_context()
    db = AsyncMock()

    slot_repo = AsyncMock()

    def _slot_get(sid: uuid.UUID):
        if sid == source_slot.id:
            return source_slot
        if sid == target_slot.id:
            return target_slot
        return None

    slot_repo.get.side_effect = _slot_get

    inst_repo = AsyncMock()

    def _inst_get(psid: uuid.UUID):
        if psid == target_slot.id:
            return target_instance
        if psid == source_slot.id:
            return source_instance
        return None

    inst_repo.get_by_planning_slot.side_effect = _inst_get

    req_repo = AsyncMock()
    req_repo.list_open_by_district.return_value = [overwrite]

    with patch("app.adapters.api.routers.invitations.require_role_in_district"):
        result = await inv_router.list_overwrite_requests(
            auth,
            db,
            district_id=district_id,
            req_repo=req_repo,
            slot_repo=slot_repo,
            instance_repo=inst_repo,
        )

    assert len(result) == 1
    assert result[0].proposed_title == "Updated Title"


@pytest.mark.asyncio
async def test_invitation_list_event_invitations_no_slot() -> None:
    """list_event_invitations returns 404 when the planning slot doesn't exist."""
    auth = _auth_context()
    db = AsyncMock()
    missing_id = uuid.uuid4()

    slot_repo = AsyncMock()
    slot_repo.get.return_value = None

    with pytest.raises(HTTPException) as exc:
        await inv_router.list_event_invitations(
            missing_id, auth, db, slot_repo=slot_repo, inv_repo=AsyncMock()
        )

    assert exc.value.status_code == 404


# ===================================================================
# ICS export: UID stability, token validation, anonymization (UC-05)
# ===================================================================


@pytest.mark.asyncio
async def test_export_calendar_ics_uid_stable_across_exports() -> None:
    """The UID line for the same slot must be identical across repeated exports."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    instance = _event_instance(planning_slot_id=slot.id)

    token = ExportToken.create(
        label="Export",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    db = _export_session(AsyncMock())
    repos = _export_repos(token=token, slots=[slot], instances=[instance])

    response1 = await export_router.export_calendar_ics(
        token.token, db, approval_status=None, **repos
    )
    response2 = await export_router.export_calendar_ics(
        token.token, db, approval_status=None, **repos
    )

    uid_line = f"UID:{slot.id}@nak-bezirksplaner".encode()
    assert uid_line in response1.body
    assert uid_line in response2.body
    # Both exports contain exactly the same UID
    assert response1.body == response2.body


@pytest.mark.asyncio
async def test_export_calendar_ics_unknown_token_returns_404() -> None:
    """An unknown export token must yield HTTP 404 without leaking token existence."""
    token_repo = AsyncMock()
    token_repo.get_by_token.return_value = None

    with pytest.raises(HTTPException) as exc:
        await export_router.export_calendar_ics(
            "unknown-token",
            AsyncMock(),
            token_repo=token_repo,
            slot_repo=AsyncMock(),
            instance_repo=AsyncMock(),
            sa_repo=AsyncMock(),
            leader_repo_dep=AsyncMock(),
        )

    assert exc.value.status_code == 404
    assert "Token ungültig" in exc.value.detail


@pytest.mark.asyncio
async def test_export_calendar_ics_public_token_anonymizes_leader() -> None:
    """PUBLIC tokens must anonymize ServiceAssignment names."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    instance = _event_instance(planning_slot_id=slot.id)

    token = ExportToken.create(
        label="Public",
        token_type=TokenType.PUBLIC,
        district_id=district_id,
        congregation_id=None,
    )
    db = _export_session(AsyncMock())
    repos = _export_repos(
        token=token,
        slots=[slot],
        instances=[instance],
        assignments=[_assignment_stub(slot.id, "Bezirksvorsteher Müller")],
    )

    response = await export_router.export_calendar_ics(
        token.token, db, approval_status=None, **repos
    )

    assert b"Dienstleiter: [Name anonymisiert]" in response.body
    assert b"Bezirksvorsteher M" not in response.body


@pytest.mark.asyncio
async def test_export_calendar_ics_internal_token_shows_full_leader_name() -> None:
    """INTERNAL tokens must show the full ServiceAssignment name."""
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    instance = _event_instance(planning_slot_id=slot.id)

    token = ExportToken.create(
        label="Internal",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    db = _export_session(AsyncMock())
    repos = _export_repos(
        token=token,
        slots=[slot],
        instances=[instance],
        assignments=[_assignment_stub(slot.id, "Bezirksvorsteher Müller")],
    )

    response = await export_router.export_calendar_ics(
        token.token, db, approval_status=None, **repos
    )

    assert b"Dienstleiter: Bezirksvorsteher M" in response.body
    assert b"[Name anonymisiert]" not in response.body


# ===================================================================
# ICS export: shared visibility rules (issue #466)
# ===================================================================


def _vevents(body: bytes) -> list[str]:
    return body.decode().split("BEGIN:VEVENT")[1:]


async def _export(token: ExportToken, slots: list, approval_status=None, **repo_kwargs):
    db = _export_session(AsyncMock())
    repos = _export_repos(token=token, slots=slots, **repo_kwargs)
    return await export_router.export_calendar_ics(
        token.token, db, approval_status=approval_status, **repos
    )


@pytest.mark.asyncio
async def test_export_congregation_feed_includes_applicable_district_slots() -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    own = _planning_slot(district_id=district_id, congregation_id=congregation_id)
    distributed = _planning_slot(
        district_id=district_id, congregation_id=None, applicability=[str(congregation_id)]
    )
    to_all = _planning_slot(district_id=district_id, congregation_id=None, applicability=["all"])
    not_distributed = _planning_slot(district_id=district_id, congregation_id=None)
    other_congregation = _planning_slot(district_id=district_id)
    token = ExportToken.create(
        label="Gemeinde",
        token_type=TokenType.PUBLIC,
        district_id=district_id,
        congregation_id=congregation_id,
    )

    response = await _export(
        token, [own, distributed, to_all, not_distributed, other_congregation]
    )

    exported = {s.id for s in (own, distributed, to_all) if str(s.id).encode() in response.body}
    assert exported == {own.id, distributed.id, to_all.id}
    assert response.body.count(b"BEGIN:VEVENT") == 3


@pytest.mark.asyncio
async def test_export_public_token_cannot_include_planned_via_query() -> None:
    district_id = uuid.uuid4()
    planned = _planning_slot(district_id=district_id, approval_status=EventApprovalStatus.PLANNED)
    token = ExportToken.create(
        label="Public",
        token_type=TokenType.PUBLIC,
        district_id=district_id,
        congregation_id=None,
    )

    response = await _export(token, [planned], approval_status="include_planned")

    assert b"BEGIN:VEVENT" not in response.body


@pytest.mark.asyncio
async def test_export_cancelled_slot_is_marked_cancelled() -> None:
    district_id = uuid.uuid4()
    cancelled = _planning_slot(district_id=district_id, status=PlanningSlotStatus.CANCELLED)
    token = ExportToken.create(
        label="Export", token_type=TokenType.PUBLIC, district_id=district_id, congregation_id=None
    )

    response = await _export(token, [cancelled])

    [vevent] = _vevents(response.body)
    assert f"UID:{cancelled.id}@nak-bezirksplaner" in vevent
    assert "STATUS:CANCELLED" in vevent


@pytest.mark.asyncio
async def test_export_change_metadata_follows_updated_at() -> None:
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    slot.created_at = datetime(2026, 1, 1, 8, 0, tzinfo=UTC)
    slot.updated_at = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
    token = ExportToken.create(
        label="Export", token_type=TokenType.INTERNAL, district_id=district_id, congregation_id=None
    )

    first = _vevents((await _export(token, [slot])).body)[0]
    slot.updated_at += timedelta(minutes=5)
    second = _vevents((await _export(token, [slot])).body)[0]

    assert "DTSTAMP:20260302T093000Z" in first
    assert "LAST-MODIFIED:20260302T093000Z" in first

    def _sequence(vevent: str) -> int:
        line = next(x for x in vevent.splitlines() if x.startswith("SEQUENCE:"))
        return int(line.removeprefix("SEQUENCE:"))

    assert _sequence(second) > _sequence(first)


def _sequence_of(vevent: str) -> int:
    line = next(x for x in vevent.splitlines() if x.startswith("SEQUENCE:"))
    return int(line.removeprefix("SEQUENCE:"))


def test_export_sequence_fits_rfc5545_integer_beyond_2038() -> None:
    assert export_router._sequence(datetime(2087, 12, 31, tzinfo=UTC)) < 2**31


@pytest.mark.asyncio
async def test_export_leader_rename_advances_revision() -> None:
    district_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    slot.updated_at = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
    leader = Leader.create(name="Alt", district_id=district_id)
    leader.updated_at = slot.updated_at
    assignment = _assignment_stub(slot.id, "", leader_id=leader.id)
    token = ExportToken.create(
        label="Export", token_type=TokenType.INTERNAL, district_id=district_id, congregation_id=None
    )

    first = _vevents(
        (await _export(token, [slot], assignments=[assignment], leaders=[leader])).body
    )[0]
    leader.name = "Neu"
    leader.updated_at += timedelta(minutes=5)
    second = _vevents(
        (await _export(token, [slot], assignments=[assignment], leaders=[leader])).body
    )[0]

    assert "Neu" in second
    assert "LAST-MODIFIED:20260302T093500Z" in second
    assert _sequence_of(second) > _sequence_of(first)


@pytest.mark.asyncio
async def test_export_congregation_rename_advances_revision() -> None:
    district_id = uuid.uuid4()
    congregation_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id, congregation_id=congregation_id)
    slot.updated_at = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
    token = ExportToken.create(
        label="Export", token_type=TokenType.INTERNAL, district_id=district_id, congregation_id=None
    )

    async def export_with(name: str, updated_at: datetime) -> str:
        db = AsyncMock()
        result = MagicMock()
        congregation = MagicMock(id=congregation_id, updated_at=updated_at)
        congregation.name = name
        result.scalars.return_value = [congregation]
        db.execute.return_value = result
        repos = _export_repos(token=token, slots=[slot])
        response = await export_router.export_calendar_ics(
            token.token, db, approval_status=None, **repos
        )
        return _vevents(response.body)[0]

    first = await export_with("Alt", slot.updated_at)
    second = await export_with("Neu", slot.updated_at + timedelta(minutes=5))

    assert "LOCATION:Neu" in second
    assert "LAST-MODIFIED:20260302T093500Z" in second
    assert _sequence_of(second) > _sequence_of(first)


@pytest.mark.asyncio
async def test_export_leader_feed_contains_only_that_leaders_slots() -> None:
    district_id = uuid.uuid4()
    leader_id = uuid.uuid4()
    mine = _planning_slot(district_id=district_id)
    someone_elses = _planning_slot(district_id=district_id)
    unassigned = _planning_slot(district_id=district_id)
    token = ExportToken.create(
        label="Leader",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
        leader_id=leader_id,
    )

    response = await _export(
        token,
        [mine, someone_elses, unassigned],
        assignments=[
            _assignment_stub(mine.id, "Ev. Ich", leader_id=leader_id),
            _assignment_stub(someone_elses.id, "Ev. Andere", leader_id=uuid.uuid4()),
        ],
    )

    [vevent] = _vevents(response.body)
    assert str(mine.id) in vevent


@pytest.mark.asyncio
async def test_export_leader_feed_uses_canonical_planning_slot_key() -> None:
    """Legacy rows whose event_id differs from planning_slot_id still match (#466)."""
    district_id = uuid.uuid4()
    leader_id = uuid.uuid4()
    slot = _planning_slot(district_id=district_id)
    legacy = _assignment_stub(slot.id, "Ev. Ich", leader_id=leader_id)
    legacy.event_id = uuid.uuid4()
    token = ExportToken.create(
        label="Leader",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
        leader_id=leader_id,
    )

    response = await _export(token, [slot], assignments=[legacy])

    [vevent] = _vevents(response.body)
    assert str(slot.id) in vevent
    assert "Dienstleiter: Ev. Ich" in vevent
