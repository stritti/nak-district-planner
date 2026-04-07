from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.api.schemas.invitation import InvitationTargetCreate
from app.application.invitation_service import (
    apply_overwrite_decision,
    create_invitations_for_event,
    propagate_source_event_update,
)
from app.domain.models.event import Event, EventSource, EventStatus, EventVisibility
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationOverwriteRequest,
    InvitationTargetType,
    OverwriteDecisionStatus,
)


def _event(congregation_id: uuid.UUID | None = None) -> Event:
    return Event.create(
        title="Gottesdienst",
        start_at=datetime(2026, 4, 10, 9, 30, tzinfo=timezone.utc),
        end_at=datetime(2026, 4, 10, 11, 30, tzinfo=timezone.utc),
        district_id=uuid.uuid4(),
        congregation_id=congregation_id,
        category="Gottesdienst",
        source=EventSource.INTERNAL,
        status=EventStatus.PUBLISHED,
        visibility=EventVisibility.INTERNAL,
    )


@pytest.mark.asyncio
async def test_create_invitations_creates_linked_event_for_internal_target():
    session = MagicMock()
    source_congregation_id = uuid.uuid4()
    target_congregation_id = uuid.uuid4()
    source_event = _event(congregation_id=source_congregation_id)

    with (
        patch("app.application.invitation_service.SqlEventRepository") as event_repo_cls,
        patch(
            "app.application.invitation_service.SqlCongregationRepository"
        ) as congregation_repo_cls,
        patch("app.application.invitation_service.SqlInvitationRepository") as invitation_repo_cls,
    ):
        event_repo = MagicMock()
        event_repo.get = AsyncMock(return_value=source_event)
        event_repo.save = AsyncMock()
        event_repo_cls.return_value = event_repo

        congregation_repo = MagicMock()
        congregation_repo.get = AsyncMock(
            return_value=MagicMock(id=target_congregation_id, district_id=source_event.district_id)
        )
        congregation_repo_cls.return_value = congregation_repo

        invitation_repo = MagicMock()
        invitation_repo.save = AsyncMock()
        invitation_repo_cls.return_value = invitation_repo

        created = await create_invitations_for_event(
            session,
            source_event_id=source_event.id,
            targets=[
                InvitationTargetCreate(
                    target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                    target_congregation_id=target_congregation_id,
                )
            ],
        )

        assert len(created) == 1
        assert created[0].target_congregation_id == target_congregation_id
        assert created[0].linked_event_id is not None
        event_repo.save.assert_called_once()
        invitation_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_propagate_source_event_creates_pending_requests():
    session = MagicMock()
    source_event = _event(congregation_id=uuid.uuid4())
    target_event = _event(congregation_id=uuid.uuid4())
    invitation = CongregationInvitation.create(
        source_event_id=source_event.id,
        source_congregation_id=source_event.congregation_id,
        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        target_congregation_id=target_event.congregation_id,
        linked_event_id=target_event.id,
    )

    with (
        patch("app.application.invitation_service.SqlInvitationRepository") as invitation_repo_cls,
        patch("app.application.invitation_service.SqlEventRepository") as event_repo_cls,
        patch(
            "app.application.invitation_service.SqlInvitationOverwriteRequestRepository"
        ) as overwrite_repo_cls,
    ):
        invitation_repo = MagicMock()
        invitation_repo.list_by_source_event = AsyncMock(return_value=[invitation])
        invitation_repo_cls.return_value = invitation_repo

        event_repo = MagicMock()
        event_repo.get = AsyncMock(return_value=target_event)
        event_repo_cls.return_value = event_repo

        overwrite_repo = MagicMock()
        overwrite_repo.list_open_by_source_event = AsyncMock(return_value=[])
        overwrite_repo.save = AsyncMock()
        overwrite_repo_cls.return_value = overwrite_repo

        requests = await propagate_source_event_update(session, source_event=source_event)
        assert len(requests) == 1
        assert requests[0].status == OverwriteDecisionStatus.PENDING_OVERWRITE
        overwrite_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_apply_overwrite_decision_accept_updates_target_event():
    session = MagicMock()
    target_event = _event(congregation_id=uuid.uuid4())
    request = InvitationOverwriteRequest.create(
        invitation_id=uuid.uuid4(),
        source_event_id=uuid.uuid4(),
        target_event_id=target_event.id,
        proposed_title="Neuer Titel",
        proposed_start_at=target_event.start_at,
        proposed_end_at=target_event.end_at,
        proposed_description="Neu",
        proposed_category="Gottesdienst",
    )

    with (
        patch(
            "app.application.invitation_service.SqlInvitationOverwriteRequestRepository"
        ) as overwrite_repo_cls,
        patch("app.application.invitation_service.SqlEventRepository") as event_repo_cls,
    ):
        overwrite_repo = MagicMock()
        overwrite_repo.get = AsyncMock(return_value=request)
        overwrite_repo.set_status = AsyncMock(
            return_value=InvitationOverwriteRequest(
                **{**request.__dict__, "status": OverwriteDecisionStatus.ACCEPTED}
            )
        )
        overwrite_repo_cls.return_value = overwrite_repo

        event_repo = MagicMock()
        event_repo.get = AsyncMock(return_value=target_event)
        event_repo.save = AsyncMock()
        event_repo_cls.return_value = event_repo

        updated = await apply_overwrite_decision(
            session,
            request_id=request.id,
            decision=OverwriteDecisionStatus.ACCEPTED,
        )

        assert updated is not None
        assert updated.status == OverwriteDecisionStatus.ACCEPTED
        assert target_event.title == "Neuer Titel"
        event_repo.save.assert_called_once_with(target_event)
