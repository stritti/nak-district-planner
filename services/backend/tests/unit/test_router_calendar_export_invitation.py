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
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlot


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


# ===================================================================
# Calendar Integration tests  (unchanged logic, only import changes)
# ===================================================================

@pytest.mark.asyncio
async def test_calendar_integration_routes_success_and_errors() -> None:
    district_id = uuid.uuid4()
    integration = _integration(district_id=district_id)
    db = AsyncMock()
    auth = _auth_context()

    with (
        patch("app.adapters.api.routers.calendar_integrations.assert_has_role_in_district"),
        patch(
            "app.adapters.api.routers.calendar_integrations.encrypt_credentials",
            return_value="enc",
        ),
        patch(
            "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
        ) as repo_cls,
        patch(
            "app.adapters.api.routers.calendar_integrations.run_sync",
            new=AsyncMock(return_value={"created": 1, "updated": 2, "cancelled": 3}),
        ),
    ):
        repo = AsyncMock()
        repo.get.return_value = integration
        repo.list_by_district.return_value = [integration]
        repo.list_active.return_value = [integration]
        repo_cls.return_value = repo

        created = await ci_router.create_calendar_integration(
            CalendarIntegrationCreate(
                district_id=district_id,
                name="Name",
                type=CalendarType.ICS,
                credentials={"u": "x"},
            ),
            auth,
            db,
        )
        listed = await ci_router.list_calendar_integrations(auth, db, district_id=district_id)
        sync = await ci_router.trigger_sync(integration.id, auth, db)
        updated = await ci_router.update_calendar_integration(
            integration.id,
            CalendarIntegrationUpdate(name="Neu"),
            auth,
            db,
        )
        await ci_router.delete_calendar_integration(integration.id, auth, db)

    assert created.name == "Name"
    assert listed.total == 1
    assert sync.created == 1
    assert updated.name == "Neu"


@pytest.mark.asyncio
async def test_calendar_integration_not_found_and_bad_sync() -> None:
    auth = _auth_context()
    with patch(
        "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
    ) as repo_cls:
        repo = AsyncMock()
        repo.get.return_value = None
        repo_cls.return_value = repo
        with pytest.raises(HTTPException):
            await ci_router.trigger_sync(uuid.uuid4(), auth, AsyncMock())
        with pytest.raises(HTTPException):
            await ci_router.update_calendar_integration(
                uuid.uuid4(),
                CalendarIntegrationUpdate(name="X"),
                auth,
                AsyncMock(),
            )
        with pytest.raises(HTTPException):
            await ci_router.delete_calendar_integration(uuid.uuid4(), auth, AsyncMock())


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

    with (
        patch("app.adapters.api.routers.calendar_integrations.assert_has_role_in_congregation"),
        patch(
            "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
        ) as repo_cls,
    ):
        repo = AsyncMock()
        repo.list_by_congregation.return_value = [integration]
        repo_cls.return_value = repo

        listed = await ci_router.list_calendar_integrations(
            auth, db, congregation_id=congregation_id
        )

    assert listed.total == 1
    assert listed.items[0].congregation_id == congregation_id


@pytest.mark.asyncio
async def test_list_calendar_integrations_congregation_scoped_validates_district() -> None:
    congregation_id = uuid.uuid4()
    other_district_id = uuid.uuid4()
    db = AsyncMock()
    auth = _auth_context()

    with (
        patch("app.adapters.api.routers.calendar_integrations.assert_has_role_in_congregation"),
        patch(
            "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
        ) as repo_cls,
        patch(
            "app.adapters.api.routers.calendar_integrations.SqlCongregationRepository"
        ) as cong_repo_cls,
    ):
        repo = AsyncMock()
        repo_cls.return_value = repo
        cong_repo = AsyncMock()
        # congregation belongs to a different district
        cong_repo.get.return_value = type("C", (), {"district_id": uuid.uuid4()})()
        cong_repo_cls.return_value = cong_repo

        with pytest.raises(HTTPException) as exc:
            await ci_router.list_calendar_integrations(
                auth,
                db,
                district_id=other_district_id,
                congregation_id=congregation_id,
            )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_calendar_integrations_congregation_scoped_forbidden() -> None:
    congregation_id = uuid.uuid4()
    db = AsyncMock()
    auth = _auth_context()

    with (
        patch(
            "app.adapters.api.routers.calendar_integrations.assert_has_role_in_congregation",
            side_effect=ci_router.PermissionError("no permission"),
        ),
        patch(
            "app.adapters.api.routers.calendar_integrations.SqlCalendarIntegrationRepository"
        ) as repo_cls,
    ):
        repo = AsyncMock()
        repo_cls.return_value = repo

        with pytest.raises(HTTPException) as exc:
            await ci_router.list_calendar_integrations(auth, db, congregation_id=congregation_id)

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

    with (
        patch("app.adapters.api.routers.export.assert_has_role_in_district"),
        patch("app.adapters.api.routers.export.SqlExportTokenRepository") as token_repo_cls,
    ):
        token_repo = AsyncMock()
        token_repo.get.return_value = token
        token_repo.get_by_token.return_value = token
        token_repo.list_by_district.return_value = [token]
        token_repo.delete.return_value = True
        token_repo_cls.return_value = token_repo

        created = await export_router.create_export_token(
            auth,
            ExportTokenCreate(
                label="X",
                token_type=TokenType.INTERNAL,
                district_id=district_id,
                congregation_id=None,
            ),
            db,
        )
        listed = await export_router.list_export_tokens(auth, db, district_id=district_id)
        await export_router.delete_export_token(auth, token.id, db)

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
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.export.SqlExportTokenRepository") as token_repo_cls,
        patch("app.adapters.api.routers.export.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.export.SqlEventInstanceRepository") as inst_repo_cls,
        patch("app.adapters.api.routers.export.SqlServiceAssignmentRepository") as sa_repo_cls,
        patch("app.adapters.api.routers.export.SqlLeaderRepository") as leader_repo_cls,
        patch("app.adapters.api.routers.export.select"),
    ):
        token_repo = AsyncMock()
        token_repo.get_by_token.return_value = token
        token_repo_cls.return_value = token_repo

        slot_repo = AsyncMock()
        slot_repo.list_for_date_range.return_value = [slot]
        slot_repo_cls.return_value = slot_repo

        inst_repo = AsyncMock()
        inst_repo.list_by_planning_slots.return_value = [instance]
        inst_repo_cls.return_value = inst_repo

        sa_repo = AsyncMock()
        sa_repo.list_by_planning_slots.return_value = []
        sa_repo_cls.return_value = sa_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = []
        leader_repo_cls.return_value = leader_repo

        session_result = MagicMock()
        session_result.scalars.return_value = []
        db.execute.return_value = session_result

        response = await export_router.export_calendar_ics(
            token.token, db, approval_status=None
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
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.export.SqlExportTokenRepository") as token_repo_cls,
        patch("app.adapters.api.routers.export.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.export.SqlEventInstanceRepository") as inst_repo_cls,
        patch("app.adapters.api.routers.export.SqlServiceAssignmentRepository") as sa_repo_cls,
        patch("app.adapters.api.routers.export.SqlLeaderRepository") as leader_repo_cls,
        patch("app.adapters.api.routers.export.select"),
    ):
        token_repo = AsyncMock()
        token_repo.get_by_token.return_value = token
        token_repo_cls.return_value = token_repo

        slot_repo = AsyncMock()
        slot_repo.list_for_date_range.return_value = [confirmed_slot, planned_slot]
        slot_repo_cls.return_value = slot_repo

        inst_repo = AsyncMock()
        inst_repo.list_by_planning_slots.return_value = [confirmed_instance]
        inst_repo_cls.return_value = inst_repo

        sa_repo = AsyncMock()
        sa_repo.list_by_planning_slots.return_value = []
        sa_repo_cls.return_value = sa_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = []
        leader_repo_cls.return_value = leader_repo

        session_result = MagicMock()
        session_result.scalars.return_value = []
        db.execute.return_value = session_result

        response = await export_router.export_calendar_ics(
            token.token, db, approval_status="confirmed_only"
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
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.export.SqlExportTokenRepository") as token_repo_cls,
        patch("app.adapters.api.routers.export.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.export.SqlEventInstanceRepository") as inst_repo_cls,
        patch("app.adapters.api.routers.export.SqlServiceAssignmentRepository") as sa_repo_cls,
        patch("app.adapters.api.routers.export.SqlLeaderRepository") as leader_repo_cls,
        patch("app.adapters.api.routers.export.select"),
    ):
        token_repo = AsyncMock()
        token_repo.get_by_token.return_value = token
        token_repo_cls.return_value = token_repo

        slot_repo = AsyncMock()
        slot_repo.list_for_date_range.return_value = [slot]
        slot_repo_cls.return_value = slot_repo

        inst_repo = AsyncMock()
        inst_repo.list_by_planning_slots.return_value = [instance]
        inst_repo_cls.return_value = inst_repo

        sa_repo = AsyncMock()
        sa_repo.list_by_planning_slots.return_value = [
            type("SA", (), {
                "event_id": slot.id,
                "planning_slot_id": slot.id,
                "leader_id": leader_id,
                "leader_name": "Bezirksvorsteher Müller",
                "status": "ASSIGNED",
            })()
        ]
        sa_repo_cls.return_value = sa_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = []
        leader_repo_cls.return_value = leader_repo

        session_result = MagicMock()
        session_result.scalars.return_value = []
        db.execute.return_value = session_result

        response = await export_router.export_calendar_ics(
            token.token, db, approval_status=None
        )

    assert b"Dienstleiter: Bezirksvorsteher M" in response.body


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
    db = AsyncMock()

    with (
        patch("app.adapters.api.routers.export.SqlExportTokenRepository") as token_repo_cls,
        patch("app.adapters.api.routers.export.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.export.SqlEventInstanceRepository") as inst_repo_cls,
        patch("app.adapters.api.routers.export.SqlServiceAssignmentRepository") as sa_repo_cls,
        patch("app.adapters.api.routers.export.SqlLeaderRepository") as leader_repo_cls,
        patch("app.adapters.api.routers.export.select"),
    ):
        token_repo = AsyncMock()
        token_repo.get_by_token.return_value = token
        token_repo_cls.return_value = token_repo

        slot_repo = AsyncMock()
        slot_repo.list_for_date_range.return_value = []
        slot_repo_cls.return_value = slot_repo

        inst_repo = AsyncMock()
        inst_repo.list_by_planning_slots.return_value = []
        inst_repo_cls.return_value = inst_repo

        sa_repo = AsyncMock()
        sa_repo.list_by_planning_slots.return_value = []
        sa_repo_cls.return_value = sa_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = []
        leader_repo_cls.return_value = leader_repo

        session_result = MagicMock()
        session_result.scalars.return_value = []
        db.execute.return_value = session_result

        response = await export_router.export_calendar_ics(
            token.token, db, approval_status=None
        )

    assert b"BEGIN:VCALENDAR" in response.body
    assert b"BEGIN:VEVENT" not in response.body


@pytest.mark.asyncio
async def test_export_token_not_found_paths() -> None:
    with patch("app.adapters.api.routers.export.SqlExportTokenRepository") as token_repo_cls:
        token_repo = AsyncMock()
        token_repo.get_by_token.return_value = None
        token_repo.get.return_value = None
        token_repo_cls.return_value = token_repo
        with pytest.raises(HTTPException):
            await export_router.export_calendar_ics("missing", AsyncMock())
        with pytest.raises(HTTPException):
            await export_router.delete_export_token(
                _auth_context(), uuid.uuid4(), AsyncMock()
            )


@pytest.mark.asyncio
async def test_export_token_write_routes_forbidden_without_permission() -> None:
    district_id = uuid.uuid4()
    token = ExportToken.create(
        label="L",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    auth = _auth_context()

    with (
        patch("app.adapters.api.routers.export.SqlExportTokenRepository") as token_repo_cls,
        patch(
            "app.adapters.api.routers.export.assert_has_role_in_district",
            side_effect=export_router.PermissionError("forbidden"),
        ),
    ):
        token_repo = AsyncMock()
        token_repo.get.return_value = token
        token_repo_cls.return_value = token_repo

        with pytest.raises(HTTPException) as create_exc:
            await export_router.create_export_token(
                auth,
                ExportTokenCreate(
                    label="X",
                    token_type=TokenType.INTERNAL,
                    district_id=district_id,
                ),
                AsyncMock(),
            )
        with pytest.raises(HTTPException) as delete_exc:
            await export_router.delete_export_token(auth, token.id, AsyncMock())

    assert create_exc.value.status_code == 403
    assert delete_exc.value.status_code == 403


@pytest.mark.asyncio
async def test_list_routes_require_district_id_for_non_superadmin() -> None:
    auth = _auth_context(is_superadmin=False)

    with pytest.raises(HTTPException) as ci_exc:
        await ci_router.list_calendar_integrations(auth, AsyncMock(), district_id=None)
    with pytest.raises(HTTPException) as export_exc:
        await export_router.list_export_tokens(auth, AsyncMock(), district_id=None)

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

    with (
        patch("app.adapters.api.routers.invitations.assert_has_role_in_district"),
        patch("app.adapters.api.routers.invitations.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlEventInstanceRepository") as inst_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlInvitationRepository") as inv_repo_cls,
        patch(
            "app.adapters.api.routers.invitations.SqlInvitationOverwriteRequestRepository"
        ) as req_repo_cls,
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
        slot_repo = AsyncMock()
        slot_repo.get.return_value = source_slot
        slot_repo_cls.return_value = slot_repo

        inst_repo = AsyncMock()
        inst_repo.get_by_planning_slot.return_value = source_instance
        inst_repo_cls.return_value = inst_repo

        inv_repo = AsyncMock()
        inv_repo.get.return_value = invitation
        inv_repo.list_by_source_event.return_value = [invitation]
        inv_repo_cls.return_value = inv_repo

        req_repo = AsyncMock()
        req_repo.get.return_value = overwrite
        req_repo.list_open_by_district.return_value = [overwrite]
        req_repo_cls.return_value = req_repo

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
        )
        listed = await inv_router.list_event_invitations(source_slot.id, auth, db)
        await inv_router.remove_invitation(invitation.id, auth, db)
        ovr = await inv_router.list_overwrite_requests(auth, db, district_id=district_id)
        decided = await inv_router.decide_overwrite_request(
            overwrite.id,
            OverwriteDecisionRequest(decision=OverwriteDecisionStatus.ACCEPTED),
            auth,
            db,
        )

    assert created and listed and ovr
    assert decided.id == overwrite.id


@pytest.mark.asyncio
async def test_invitation_not_found_paths() -> None:
    auth = _auth_context()
    slot_id = uuid.uuid4()

    with (
        patch("app.adapters.api.routers.invitations.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlInvitationRepository") as inv_repo_cls,
        patch(
            "app.adapters.api.routers.invitations.SqlInvitationOverwriteRequestRepository"
        ) as req_repo_cls,
    ):
        slot_repo = AsyncMock()
        slot_repo.get.return_value = None
        slot_repo_cls.return_value = slot_repo
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
            )

        inv_repo = AsyncMock()
        inv_repo.get.return_value = None
        inv_repo_cls.return_value = inv_repo
        with pytest.raises(HTTPException):
            await inv_router.remove_invitation(uuid.uuid4(), auth, AsyncMock())

        req_repo = AsyncMock()
        req_repo.get.return_value = None
        req_repo_cls.return_value = req_repo
        with pytest.raises(HTTPException):
            await inv_router.decide_overwrite_request(
                uuid.uuid4(),
                OverwriteDecisionRequest(decision=OverwriteDecisionStatus.ACCEPTED),
                auth,
                AsyncMock(),
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

    with (
        patch("app.adapters.api.routers.invitations.assert_has_role_in_district"),
        patch("app.adapters.api.routers.invitations.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlEventInstanceRepository") as inst_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlInvitationRepository") as inv_repo_cls,
        patch(
            "app.adapters.api.routers.invitations.SqlInvitationOverwriteRequestRepository"
        ),
        patch(
            "app.adapters.api.routers.invitations.create_invitations_for_event",
            new=AsyncMock(return_value=[invitation]),
        ),
    ):
        slot_repo = AsyncMock()
        slot_repo.get.return_value = source_slot
        slot_repo_cls.return_value = slot_repo

        inst_repo = AsyncMock()
        inst_repo.get_by_planning_slot.return_value = source_instance
        inst_repo_cls.return_value = inst_repo

        inv_repo = AsyncMock()
        inv_repo.list_by_source_event.return_value = [invitation]
        inv_repo_cls.return_value = inv_repo

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

    with (
        patch("app.adapters.api.routers.invitations.SqlInvitationRepository") as inv_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlPlanningSlotRepository") as slot_repo_cls,
    ):
        inv_repo = AsyncMock()
        inv_repo.get.return_value = invitation
        inv_repo_cls.return_value = inv_repo

        slot_repo = AsyncMock()
        slot_repo.get.return_value = None  # planning slot not found
        slot_repo_cls.return_value = slot_repo

        with pytest.raises(HTTPException) as exc:
            await inv_router.remove_invitation(invitation.id, auth, db)

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

    with (
        patch("app.adapters.api.routers.invitations.assert_has_role_in_district"),
        patch("app.adapters.api.routers.invitations.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlEventInstanceRepository") as inst_repo_cls,
        patch(
            "app.adapters.api.routers.invitations.SqlInvitationOverwriteRequestRepository"
        ) as req_repo_cls,
    ):
        slot_repo = AsyncMock()

        def _slot_get(sid: uuid.UUID):
            if sid == source_slot.id:
                return source_slot
            if sid == target_slot.id:
                return target_slot
            return None

        slot_repo.get.side_effect = _slot_get
        slot_repo_cls.return_value = slot_repo

        inst_repo = AsyncMock()

        def _inst_get(psid: uuid.UUID):
            if psid == target_slot.id:
                return target_instance
            if psid == source_slot.id:
                return source_instance
            return None

        inst_repo.get_by_planning_slot.side_effect = _inst_get
        inst_repo_cls.return_value = inst_repo

        req_repo = AsyncMock()
        req_repo.list_open_by_district.return_value = [overwrite]
        req_repo_cls.return_value = req_repo

        result = await inv_router.list_overwrite_requests(auth, db, district_id=district_id)

    assert len(result) == 1
    assert result[0].proposed_title == "Updated Title"


@pytest.mark.asyncio
async def test_invitation_list_event_invitations_no_slot() -> None:
    """list_event_invitations returns 404 when the planning slot doesn't exist."""
    auth = _auth_context()
    db = AsyncMock()
    missing_id = uuid.uuid4()

    with patch(
        "app.adapters.api.routers.invitations.SqlPlanningSlotRepository"
    ) as slot_repo_cls:
        slot_repo = AsyncMock()
        slot_repo.get.return_value = None
        slot_repo_cls.return_value = slot_repo

        with pytest.raises(HTTPException) as exc:
            await inv_router.list_event_invitations(missing_id, auth, db)

    assert exc.value.status_code == 404
