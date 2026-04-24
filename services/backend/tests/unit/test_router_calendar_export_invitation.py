from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone
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
from app.domain.models.event import Event, EventStatus
from app.domain.models.export_token import ExportToken, TokenType
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationOverwriteRequest,
    InvitationTargetType,
    OverwriteDecisionStatus,
)


@pytest.mark.asyncio
async def test_calendar_integration_routes_success_and_errors() -> None:
    district_id = uuid.uuid4()
    integration = CalendarIntegration.create(
        district_id=district_id,
        name="ICS",
        type=CalendarType.ICS,
        credentials_enc="enc",
        capabilities=[CalendarCapability.READ],
    )
    db = AsyncMock()
    auth = type("A", (), {"memberships": [], "user_sub": "u"})()

    with (
        patch("app.adapters.api.routers.calendar_integrations.assert_has_role_in_district"),
        patch(
            "app.adapters.api.routers.calendar_integrations.encrypt_credentials", return_value="enc"
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
    auth = type("A", (), {"memberships": [], "user_sub": "u"})()
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
async def test_export_token_routes_and_ics_export() -> None:
    district_id = uuid.uuid4()
    auth = type("A", (), {"memberships": [], "user_sub": "u", "user": None})()
    token = ExportToken.create(
        label="L",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    event = Event.create(
        title="GD",
        start_at=datetime.now(UTC),
        end_at=datetime.now(UTC) + timedelta(hours=1),
        district_id=district_id,
        status=EventStatus.PUBLISHED,
    )
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.export.assert_has_role_in_district"),
        patch("app.adapters.api.routers.export.SqlExportTokenRepository") as token_repo_cls,
        patch("app.adapters.api.routers.export.SqlEventRepository") as event_repo_cls,
        patch("app.adapters.api.routers.export.SqlServiceAssignmentRepository") as sa_repo_cls,
        patch("app.adapters.api.routers.export.SqlLeaderRepository") as leader_repo_cls,
        patch("app.adapters.api.routers.export.select"),
    ):
        token_repo = AsyncMock()
        token_repo.get_by_token.return_value = token
        token_repo.get.return_value = token
        token_repo.list_by_district.return_value = [token]
        token_repo.delete.return_value = True
        token_repo_cls.return_value = token_repo

        event_repo = AsyncMock()
        event_repo.list.return_value = ([event], 1)
        event_repo_cls.return_value = event_repo

        sa_repo = AsyncMock()
        sa_repo.list_by_events.return_value = []
        sa_repo_cls.return_value = sa_repo

        leader_repo = AsyncMock()
        leader_repo.list_by_district.return_value = []
        leader_repo_cls.return_value = leader_repo

        session_result = MagicMock()
        session_result.scalars.return_value = []
        db.execute.return_value = session_result

        created = await export_router.create_export_token(
            object(),
            ExportTokenCreate(
                label="X",
                token_type=TokenType.INTERNAL,
                district_id=district_id,
                congregation_id=None,
            ),
            db,
        )
        listed = await export_router.list_export_tokens(auth, db, district_id=district_id)
        ics = await export_router.export_calendar_ics(token.token, db)
        await export_router.delete_export_token(object(), token.id, db)

    assert created.label == "X"
    assert listed
    assert b"BEGIN:VCALENDAR" in ics.body


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
            await export_router.delete_export_token(object(), uuid.uuid4(), AsyncMock())


@pytest.mark.asyncio
async def test_export_token_write_routes_forbidden_without_permission() -> None:
    district_id = uuid.uuid4()
    token = ExportToken.create(
        label="L",
        token_type=TokenType.INTERNAL,
        district_id=district_id,
        congregation_id=None,
    )
    auth = type("A", (), {"memberships": [], "user_sub": "u", "user": None})()

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
    auth = type(
        "A",
        (),
        {
            "memberships": [],
            "user_sub": "u",
            "user": type("U", (), {"is_superadmin": False})(),
        },
    )()

    with pytest.raises(HTTPException) as ci_exc:
        await ci_router.list_calendar_integrations(auth, AsyncMock(), district_id=None)
    with pytest.raises(HTTPException) as export_exc:
        await export_router.list_export_tokens(auth, AsyncMock(), district_id=None)

    assert ci_exc.value.status_code == 403
    assert export_exc.value.status_code == 403


@pytest.mark.asyncio
async def test_invitation_routes_success_and_error_paths() -> None:
    district_id = uuid.uuid4()
    event = Event.create(
        title="Quelle",
        start_at=datetime.now(UTC),
        end_at=datetime.now(UTC) + timedelta(hours=1),
        district_id=district_id,
    )
    invitation = CongregationInvitation.create(
        source_event_id=event.id,
        source_congregation_id=uuid.uuid4(),
        target_type=InvitationTargetType.EXTERNAL_NOTE,
        external_target_note="extern",
    )
    overwrite = InvitationOverwriteRequest.create(
        invitation_id=invitation.id,
        source_event_id=event.id,
        target_event_id=event.id,
        proposed_title="N",
        proposed_start_at=event.start_at,
        proposed_end_at=event.end_at,
        proposed_description=None,
        proposed_category=None,
    )
    auth = type("A", (), {"memberships": [], "user_sub": "u"})()
    db = AsyncMock()
    with (
        patch("app.adapters.api.routers.invitations.assert_has_role_in_district"),
        patch("app.adapters.api.routers.invitations.SqlEventRepository") as event_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlInvitationRepository") as inv_repo_cls,
        patch(
            "app.adapters.api.routers.invitations.SqlInvitationOverwriteRequestRepository"
        ) as req_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlCongregationRepository") as cong_repo_cls,
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
        event_repo = AsyncMock()
        event_repo.get.return_value = event
        event_repo_cls.return_value = event_repo

        inv_repo = AsyncMock()
        inv_repo.get.return_value = invitation
        inv_repo.list_by_source_event.return_value = [invitation]
        inv_repo_cls.return_value = inv_repo

        req_repo = AsyncMock()
        req_repo.get.return_value = overwrite
        req_repo.list_open_by_district.return_value = [overwrite]
        req_repo_cls.return_value = req_repo

        cong_repo = AsyncMock()
        cong_repo.get.return_value = None
        cong_repo_cls.return_value = cong_repo

        created = await inv_router.create_invitations(
            event.id,
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
        listed = await inv_router.list_event_invitations(event.id, auth, db)
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
    auth = type("A", (), {"memberships": [], "user_sub": "u"})()
    with (
        patch("app.adapters.api.routers.invitations.SqlEventRepository") as event_repo_cls,
        patch("app.adapters.api.routers.invitations.SqlInvitationRepository") as inv_repo_cls,
        patch(
            "app.adapters.api.routers.invitations.SqlInvitationOverwriteRequestRepository"
        ) as req_repo_cls,
    ):
        event_repo = AsyncMock()
        event_repo.get.return_value = None
        event_repo_cls.return_value = event_repo
        with pytest.raises(HTTPException):
            await inv_router.create_invitations(
                uuid.uuid4(),
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
