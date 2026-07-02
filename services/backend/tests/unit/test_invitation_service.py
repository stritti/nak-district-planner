"""Tests for app.application.invitation_service (Event-free architecture)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.api.schemas.invitation import InvitationTargetCreate
from app.application.invitation_service import (
    apply_overwrite_decision,
    create_invitations_for_event,
    delete_invitation,
    propagate_source_event_update,
    sync_linked_invitation_event_schedule,
)
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationOverwriteRequest,
    InvitationTargetType,
    OverwriteDecisionStatus,
)
from app.domain.models.planning_slot import EventApprovalStatus, PlanningSlot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _planning_slot(**overrides):
    return PlanningSlot.create(
        district_id=overrides.get("district_id", uuid.uuid4()),
        planning_date=overrides.get("planning_date", date(2026, 4, 10)),
        planning_time=overrides.get("planning_time", time(9, 30)),
        congregation_id=overrides.get("congregation_id", uuid.uuid4()),
        category=overrides.get("category", "Gottesdienst"),
        title=overrides.get("title", "Gottesdienst"),
        approval_status=overrides.get("approval_status", EventApprovalStatus.CONFIRMED),
    )


def _event_instance(planning_slot_id: uuid.UUID, **overrides):
    return EventInstance.create(
        planning_slot_id=planning_slot_id,
        title=overrides.get("title", "Gottesdienst"),
        actual_start_at=overrides.get(
            "actual_start_at", datetime(2026, 4, 10, 9, 30, tzinfo=UTC)
        ),
        actual_end_at=overrides.get(
            "actual_end_at", datetime(2026, 4, 10, 11, 30, tzinfo=UTC)
        ),
        source=overrides.get("source", EventSource.INTERNAL),
        visibility=overrides.get("visibility", EventVisibility.INTERNAL),
    )


def _fake_congregation(congregation_id: uuid.UUID, district_id: uuid.UUID):
    return MagicMock(id=congregation_id, district_id=district_id)


# =========================================================================
# create_invitations_for_event
# =========================================================================


@pytest.mark.asyncio
async def test_create_invitations_creates_invitations_for_internal_targets():
        """Creates PlanningSlot + EventInstance + Invitation per internal target."""
        session = MagicMock()
        district_id = uuid.uuid4()
        source_congregation_id = uuid.uuid4()
        target_id_1 = uuid.uuid4()
        target_id_2 = uuid.uuid4()
        
        source_slot = _planning_slot(
            congregation_id=source_congregation_id, district_id=district_id
        )
        source_instance = _event_instance(source_slot.id)
        
        with (
            patch(
                "app.application.invitation_service.SqlPlanningSlotRepository"
            ) as slot_repo_cls,
            patch(
                "app.application.invitation_service.SqlEventInstanceRepository"
            ) as instance_repo_cls,
            patch(
                "app.application.invitation_service.SqlCongregationRepository"
            ) as cong_repo_cls,
            patch(
                "app.application.invitation_service.SqlInvitationRepository"
            ) as inv_repo_cls,
        ):
            slot_repo = MagicMock()
            slot_repo.get = AsyncMock(return_value=source_slot)
            slot_repo.save = AsyncMock()
            slot_repo_cls.return_value = slot_repo
            
            instance_repo = MagicMock()
            instance_repo.get_by_planning_slot = AsyncMock(return_value=source_instance)
            instance_repo.save = AsyncMock()
            instance_repo_cls.return_value = instance_repo
            
            cong_repo = MagicMock()
            cong_repo.get = AsyncMock(
                side_effect=[
                    _fake_congregation(target_id_1, district_id),
                    _fake_congregation(target_id_2, district_id),
                ]
            )
            cong_repo_cls.return_value = cong_repo
            
            inv_repo = MagicMock()
            inv_repo.list_by_source_planning_slot = AsyncMock(return_value=[])
            inv_repo.save = AsyncMock()
            inv_repo_cls.return_value = inv_repo
            
            targets = [
                InvitationTargetCreate(
                    target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                    target_congregation_id=target_id_1,
                ),
                InvitationTargetCreate(
                    target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                    target_congregation_id=target_id_2,
                ),
            ]
            
            created = await create_invitations_for_event(
                session,
                source_planning_slot_id=source_slot.id,
                targets=targets,
            )
        
        assert len(created) == 2
        assert created[0].target_congregation_id == target_id_1
        assert created[1].target_congregation_id == target_id_2
        # linked_event_id points to the target PlanningSlot
        assert created[0].linked_event_id is not None
        assert created[1].linked_event_id is not None
        assert created[0].linked_event_id != created[1].linked_event_id
        
        # Each target gets a PlanningSlot + EventInstance + Invitation created
        assert slot_repo.save.call_count == 2
        assert instance_repo.save.call_count == 2
        assert inv_repo.save.call_count == 2
        
        # Verify target PlanningSlots have invitation source fields set
        for call_args in slot_repo.save.call_args_list:
            saved_slot: PlanningSlot = call_args[0][0]
            assert saved_slot.invitation_source_congregation_id == source_congregation_id
            assert saved_slot.invitation_source_event_id == source_slot.id
            assert saved_slot.district_id == district_id
        
        # Verify target EventInstances used source data
        for call_args in instance_repo.save.call_args_list:
            saved_instance: EventInstance = call_args[0][0]
            assert saved_instance.title == source_instance.title
            assert saved_instance.actual_start_at == source_instance.actual_start_at
            assert saved_instance.actual_end_at == source_instance.actual_end_at
            assert saved_instance.source == source_instance.source
        
        # Verify target EventInstances have the correct visibility
        for call_args in instance_repo.save.call_args_list:
            saved_instance: EventInstance = call_args[0][0]
            assert saved_instance.visibility == EventVisibility.INTERNAL
        


@pytest.mark.asyncio
async def test_create_invitations_dedup_updates_existing_invitation():
    """When an invitation already exists for a target, it is updated in-place."""
    session = MagicMock()
    district_id = uuid.uuid4()
    source_congregation_id = uuid.uuid4()
    target_congregation_id = uuid.uuid4()

    source_slot = _planning_slot(
        congregation_id=source_congregation_id, district_id=district_id
    )
    source_instance = _event_instance(source_slot.id)

    existing_inv = CongregationInvitation.create(
        source_event_id=source_slot.id,
        source_planning_slot_id=source_slot.id,
        source_congregation_id=source_congregation_id,
        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        target_congregation_id=target_congregation_id,
    )

    with (
        patch(
            "app.application.invitation_service.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.application.invitation_service.SqlEventInstanceRepository"
        ) as instance_repo_cls,
        patch(
            "app.application.invitation_service.SqlCongregationRepository"
        ) as cong_repo_cls,
        patch(
            "app.application.invitation_service.SqlInvitationRepository"
        ) as inv_repo_cls,
    ):
        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=source_slot)
        slot_repo.save = AsyncMock()
        slot_repo_cls.return_value = slot_repo

        instance_repo = MagicMock()
        instance_repo.get_by_planning_slot = AsyncMock(return_value=source_instance)
        instance_repo.save = AsyncMock()
        instance_repo_cls.return_value = instance_repo

        cong_repo = MagicMock()
        cong_repo.get = AsyncMock(
            return_value=_fake_congregation(target_congregation_id, district_id)
        )
        cong_repo_cls.return_value = cong_repo

        inv_repo = MagicMock()
        inv_repo.list_by_source_planning_slot = AsyncMock(
            return_value=[existing_inv]
        )
        inv_repo.save = AsyncMock()
        inv_repo_cls.return_value = inv_repo

        targets = [
            InvitationTargetCreate(
                target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                target_congregation_id=target_congregation_id,
            ),
        ]

        created = await create_invitations_for_event(
            session,
            source_planning_slot_id=source_slot.id,
            targets=targets,
        )

    assert len(created) == 1
    assert created[0].target_congregation_id == target_congregation_id
    # No new slot/instance created
    slot_repo.save.assert_not_called()
    instance_repo.save.assert_not_called()
    # Existing invitation was saved (updated)
    inv_repo.save.assert_called_once_with(existing_inv)


@pytest.mark.asyncio
async def test_create_invitations_requires_source_congregation():
    """ValueError when source PlanningSlot has no congregation."""
    session = MagicMock()
    source_slot = _planning_slot(congregation_id=None)

    with patch(
        "app.application.invitation_service.SqlPlanningSlotRepository"
    ) as slot_repo_cls:
        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=source_slot)
        slot_repo_cls.return_value = slot_repo

        with pytest.raises(ValueError, match="assigned to a congregation"):
            await create_invitations_for_event(
                session,
                source_planning_slot_id=source_slot.id,
                targets=[],
            )


@pytest.mark.asyncio
async def test_create_invitations_requires_same_district():
    """ValueError when target congregation is in a different district."""
    session = MagicMock()
    district_id = uuid.uuid4()
    source_congregation_id = uuid.uuid4()
    target_congregation_id = uuid.uuid4()

    source_slot = _planning_slot(
        congregation_id=source_congregation_id, district_id=district_id
    )
    source_instance = _event_instance(source_slot.id)

    with (
        patch(
            "app.application.invitation_service.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.application.invitation_service.SqlEventInstanceRepository"
        ) as instance_repo_cls,
        patch(
            "app.application.invitation_service.SqlCongregationRepository"
        ) as cong_repo_cls,
        patch(
            "app.application.invitation_service.SqlInvitationRepository"
        ) as inv_repo_cls,
    ):
        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=source_slot)
        slot_repo_cls.return_value = slot_repo

        instance_repo = MagicMock()
        instance_repo.get_by_planning_slot = AsyncMock(return_value=source_instance)
        instance_repo_cls.return_value = instance_repo

        # Target congregation belongs to a different district
        cong_repo = MagicMock()
        cong_repo.get = AsyncMock(
            return_value=_fake_congregation(target_congregation_id, uuid.uuid4())
        )
        cong_repo_cls.return_value = cong_repo

        inv_repo = MagicMock()
        inv_repo.list_by_source_planning_slot = AsyncMock(return_value=[])
        inv_repo_cls.return_value = inv_repo

        targets = [
            InvitationTargetCreate(
                target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                target_congregation_id=target_congregation_id,
            ),
        ]

        with pytest.raises(ValueError, match="must belong to source district"):
            await create_invitations_for_event(
                session,
                source_planning_slot_id=source_slot.id,
                targets=targets,
            )


@pytest.mark.asyncio
async def test_create_invitations_fallback_no_event_instance():
    """Without an EventInstance, derives target EventInstance from PlanningSlot."""
    session = MagicMock()
    district_id = uuid.uuid4()
    source_congregation_id = uuid.uuid4()
    target_congregation_id = uuid.uuid4()

    source_slot = _planning_slot(
        congregation_id=source_congregation_id,
        district_id=district_id,
        title="Nur Slot",
    )

    with (
        patch(
            "app.application.invitation_service.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.application.invitation_service.SqlEventInstanceRepository"
        ) as instance_repo_cls,
        patch(
            "app.application.invitation_service.SqlCongregationRepository"
        ) as cong_repo_cls,
        patch(
            "app.application.invitation_service.SqlInvitationRepository"
        ) as inv_repo_cls,
    ):
        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=source_slot)
        slot_repo.save = AsyncMock()
        slot_repo_cls.return_value = slot_repo

        # No EventInstance for this PlanningSlot
        instance_repo = MagicMock()
        instance_repo.get_by_planning_slot = AsyncMock(return_value=None)
        instance_repo.save = AsyncMock()
        instance_repo_cls.return_value = instance_repo

        cong_repo = MagicMock()
        cong_repo.get = AsyncMock(
            return_value=_fake_congregation(target_congregation_id, district_id)
        )
        cong_repo_cls.return_value = cong_repo

        inv_repo = MagicMock()
        inv_repo.list_by_source_planning_slot = AsyncMock(return_value=[])
        inv_repo.save = AsyncMock()
        inv_repo_cls.return_value = inv_repo

        targets = [
            InvitationTargetCreate(
                target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                target_congregation_id=target_congregation_id,
            ),
        ]

        created = await create_invitations_for_event(
            session,
            source_planning_slot_id=source_slot.id,
            targets=targets,
        )

    assert len(created) == 1
    slot_repo.save.assert_called_once()
    instance_repo.save.assert_called_once()

    saved_instance: EventInstance = instance_repo.save.call_args[0][0]
    assert saved_instance.title == "Nur Slot"
    # Derives start/end from PlanningSlot date+time
    assert saved_instance.actual_start_at == datetime(2026, 4, 10, 9, 30, tzinfo=UTC)
    assert saved_instance.actual_end_at == datetime(2026, 4, 10, 10, 30, tzinfo=UTC)
    assert saved_instance.source == EventSource.INTERNAL
    assert saved_instance.visibility == EventVisibility.INTERNAL


# =========================================================================
# propagate_source_event_update
# =========================================================================


@pytest.mark.asyncio
async def test_propagate_source_event_update_no_invitations():
    """Returns empty list when no invitations exist for the source slot."""
    session = MagicMock()
    source_slot = _planning_slot()

    with patch(
        "app.application.invitation_service.SqlInvitationRepository"
    ) as inv_repo_cls:
        inv_repo = MagicMock()
        inv_repo.list_by_source_planning_slot = AsyncMock(return_value=[])
        inv_repo_cls.return_value = inv_repo

        result = await propagate_source_event_update(
            session, source_slot=source_slot
        )

    assert result == []


@pytest.mark.asyncio
async def test_propagate_source_event_update_with_invitations():
    """Returns empty list when invitations exist (no overwrite logic yet)."""
    session = MagicMock()
    source_slot = _planning_slot()
    assert source_slot.congregation_id is not None
    invitation = CongregationInvitation.create(
        source_event_id=source_slot.id,
        source_planning_slot_id=source_slot.id,
        source_congregation_id=source_slot.congregation_id,
        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        target_congregation_id=uuid.uuid4(),
    )

    with (
        patch(
            "app.application.invitation_service.SqlInvitationRepository"
        ) as inv_repo_cls,
        patch(
            "app.application.invitation_service.SqlInvitationOverwriteRequestRepository"
        ) as ow_repo_cls,
    ):
        inv_repo = MagicMock()
        inv_repo.list_by_source_planning_slot = AsyncMock(return_value=[invitation])
        inv_repo_cls.return_value = inv_repo

        ow_repo = MagicMock()
        ow_repo.list_open_by_source_event = AsyncMock(return_value=[])
        ow_repo_cls.return_value = ow_repo

        result = await propagate_source_event_update(
            session, source_slot=source_slot
        )

    # Currently returns [] (placeholder — actual logic is TODO)
    assert result == []


# =========================================================================
# apply_overwrite_decision
# =========================================================================


@pytest.mark.asyncio
async def test_apply_overwrite_accept():
    """Accepts a pending overwrite request."""
    session = MagicMock()
    request_id = uuid.uuid4()

    request = InvitationOverwriteRequest.create(
        invitation_id=uuid.uuid4(),
        source_event_id=uuid.uuid4(),
        target_event_id=uuid.uuid4(),
        proposed_title="Neuer Titel",
        proposed_start_at=datetime(2026, 5, 14, 18, 0, tzinfo=UTC),
        proposed_end_at=datetime(2026, 5, 14, 19, 30, tzinfo=UTC),
        proposed_description="Neu",
        proposed_category="Gottesdienst",
    )

    accepted_request = InvitationOverwriteRequest(
        id=request.id,
        invitation_id=request.invitation_id,
        source_event_id=request.source_event_id,
        target_event_id=request.target_event_id,
        proposed_title=request.proposed_title,
        proposed_start_at=request.proposed_start_at,
        proposed_end_at=request.proposed_end_at,
        proposed_description=request.proposed_description,
        proposed_category=request.proposed_category,
        status=OverwriteDecisionStatus.ACCEPTED,
        decided_at=datetime.now(UTC),
        created_at=request.created_at,
        updated_at=datetime.now(UTC),
    )

    with patch(
        "app.application.invitation_service.SqlInvitationOverwriteRequestRepository"
    ) as ow_repo_cls:
        ow_repo = MagicMock()
        ow_repo.get = AsyncMock(return_value=request)
        ow_repo.set_status = AsyncMock(return_value=accepted_request)
        ow_repo_cls.return_value = ow_repo

        updated = await apply_overwrite_decision(
            session,
            request_id=request_id,
            decision=OverwriteDecisionStatus.ACCEPTED,
        )

    assert updated is not None
    assert updated.status == OverwriteDecisionStatus.ACCEPTED
    ow_repo.set_status.assert_called_once_with(request.id, OverwriteDecisionStatus.ACCEPTED)


@pytest.mark.asyncio
async def test_apply_overwrite_reject():
    """Rejects a pending overwrite request."""
    session = MagicMock()
    request_id = uuid.uuid4()

    request = InvitationOverwriteRequest.create(
        invitation_id=uuid.uuid4(),
        source_event_id=uuid.uuid4(),
        target_event_id=uuid.uuid4(),
        proposed_title="Titel",
        proposed_start_at=datetime(2026, 5, 14, 18, 0, tzinfo=UTC),
        proposed_end_at=datetime(2026, 5, 14, 19, 30, tzinfo=UTC),
        proposed_description=None,
        proposed_category="Gottesdienst",
    )

    rejected_request = InvitationOverwriteRequest(
        id=request.id,
        invitation_id=request.invitation_id,
        source_event_id=request.source_event_id,
        target_event_id=request.target_event_id,
        proposed_title=request.proposed_title,
        proposed_start_at=request.proposed_start_at,
        proposed_end_at=request.proposed_end_at,
        proposed_description=request.proposed_description,
        proposed_category=request.proposed_category,
        status=OverwriteDecisionStatus.REJECTED,
        decided_at=datetime.now(UTC),
        created_at=request.created_at,
        updated_at=datetime.now(UTC),
    )

    with patch(
        "app.application.invitation_service.SqlInvitationOverwriteRequestRepository"
    ) as ow_repo_cls:
        ow_repo = MagicMock()
        ow_repo.get = AsyncMock(return_value=request)
        ow_repo.set_status = AsyncMock(return_value=rejected_request)
        ow_repo_cls.return_value = ow_repo

        updated = await apply_overwrite_decision(
            session,
            request_id=request_id,
            decision=OverwriteDecisionStatus.REJECTED,
        )

    assert updated is not None
    assert updated.status == OverwriteDecisionStatus.REJECTED
    ow_repo.set_status.assert_called_once_with(request.id, OverwriteDecisionStatus.REJECTED)


@pytest.mark.asyncio
async def test_apply_overwrite_not_found():
    """Returns None when the request does not exist."""
    session = MagicMock()

    with patch(
        "app.application.invitation_service.SqlInvitationOverwriteRequestRepository"
    ) as ow_repo_cls:
        ow_repo = MagicMock()
        ow_repo.get = AsyncMock(return_value=None)
        ow_repo_cls.return_value = ow_repo

        result = await apply_overwrite_decision(
            session,
            request_id=uuid.uuid4(),
            decision=OverwriteDecisionStatus.ACCEPTED,
        )

    assert result is None


@pytest.mark.asyncio
async def test_apply_overwrite_already_decided():
    """Returns the request unchanged if it is not PENDING."""
    session = MagicMock()

    request = InvitationOverwriteRequest.create(
        invitation_id=uuid.uuid4(),
        source_event_id=uuid.uuid4(),
        target_event_id=uuid.uuid4(),
        proposed_title="Titel",
        proposed_start_at=datetime(2026, 5, 14, 18, 0, tzinfo=UTC),
        proposed_end_at=datetime(2026, 5, 14, 19, 30, tzinfo=UTC),
        proposed_description=None,
        proposed_category="Gottesdienst",
    )
    # Simulate already decided
    request.status = OverwriteDecisionStatus.ACCEPTED

    with patch(
        "app.application.invitation_service.SqlInvitationOverwriteRequestRepository"
    ) as ow_repo_cls:
        ow_repo = MagicMock()
        ow_repo.get = AsyncMock(return_value=request)
        ow_repo_cls.return_value = ow_repo

        result = await apply_overwrite_decision(
            session,
            request_id=uuid.uuid4(),
            decision=OverwriteDecisionStatus.ACCEPTED,
        )

    # Should return the request as-is without calling set_status
    assert result is request
    ow_repo.set_status.assert_not_called()


# =========================================================================
# delete_invitation
# =========================================================================


@pytest.mark.asyncio
async def test_delete_invitation_removes_linked_slot_and_instance():
    """Deletes linked PlanningSlot + EventInstance when linked_event_id is set."""
    session = MagicMock()
    target_slot_id = uuid.uuid4()
    target_instance_id = uuid.uuid4()

    invitation = CongregationInvitation.create(
        source_event_id=uuid.uuid4(),
        source_congregation_id=uuid.uuid4(),
        target_type=InvitationTargetType.DISTRICT_CONGREGATION,
        target_congregation_id=uuid.uuid4(),
        linked_event_id=target_slot_id,
    )

    target_slot = _planning_slot()
    target_instance = _event_instance(target_slot_id)
    target_instance.id = target_instance_id

    with (
        patch(
            "app.application.invitation_service.SqlInvitationRepository"
        ) as inv_repo_cls,
        patch(
            "app.application.invitation_service.SqlPlanningSlotRepository"
        ) as slot_repo_cls,
        patch(
            "app.application.invitation_service.SqlEventInstanceRepository"
        ) as instance_repo_cls,
    ):
        inv_repo = MagicMock()
        inv_repo.get = AsyncMock(return_value=invitation)
        inv_repo.delete = AsyncMock()
        inv_repo_cls.return_value = inv_repo

        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=target_slot)
        slot_repo.delete = AsyncMock()
        slot_repo_cls.return_value = slot_repo

        instance_repo = MagicMock()
        instance_repo.get_by_planning_slot = AsyncMock(return_value=target_instance)
        instance_repo.delete = AsyncMock()
        instance_repo_cls.return_value = instance_repo

        result = await delete_invitation(session, invitation_id=invitation.id)

    assert result is True
    instance_repo.delete.assert_called_once_with(target_instance_id)
    slot_repo.delete.assert_called_once_with(target_slot.id)
    inv_repo.delete.assert_called_once_with(invitation.id)


@pytest.mark.asyncio
async def test_delete_invitation_no_linked_event():
    """Only deletes the invitation when linked_event_id is None."""
    session = MagicMock()
    invitation = CongregationInvitation.create(
        source_event_id=uuid.uuid4(),
        source_congregation_id=uuid.uuid4(),
        target_type=InvitationTargetType.EXTERNAL_NOTE,
        target_congregation_id=None,
        external_target_note="External note",
        linked_event_id=None,
    )

    with patch(
        "app.application.invitation_service.SqlInvitationRepository"
    ) as inv_repo_cls:
        inv_repo = MagicMock()
        inv_repo.get = AsyncMock(return_value=invitation)
        inv_repo.delete = AsyncMock()
        inv_repo_cls.return_value = inv_repo

        result = await delete_invitation(session, invitation_id=invitation.id)

    assert result is True
    inv_repo.delete.assert_called_once_with(invitation.id)


@pytest.mark.asyncio
async def test_delete_invitation_not_found():
    """Returns False when the invitation does not exist."""
    session = MagicMock()

    with patch(
        "app.application.invitation_service.SqlInvitationRepository"
    ) as inv_repo_cls:
        inv_repo = MagicMock()
        inv_repo.get = AsyncMock(return_value=None)
        inv_repo_cls.return_value = inv_repo

        result = await delete_invitation(session, invitation_id=uuid.uuid4())

    assert result is False
    inv_repo.delete.assert_not_called()


# =========================================================================
# sync_linked_invitation_event_schedule
# =========================================================================


@pytest.mark.asyncio
async def test_create_invitations_slot_not_found():
    """Raises ValueError when source planning slot is not found."""
    session = MagicMock()

    with patch("app.application.invitation_service.SqlPlanningSlotRepository") as slot_repo_cls:
        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=None)
        slot_repo_cls.return_value = slot_repo

        with pytest.raises(ValueError, match="PlanningSlot not found"):
            await create_invitations_for_event(
                session,
                source_planning_slot_id=uuid.uuid4(),
                targets=[],
            )


@pytest.mark.asyncio
async def test_create_invitations_target_congregation_not_found():
    """Raises ValueError when target congregation is not found."""
    session = MagicMock()
    district_id = uuid.uuid4()
    source_congregation_id = uuid.uuid4()
    target_id = uuid.uuid4()

    source_slot = _planning_slot(
        congregation_id=source_congregation_id, district_id=district_id
    )
    source_instance = _event_instance(source_slot.id)

    with (
        patch("app.application.invitation_service.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.application.invitation_service.SqlEventInstanceRepository") as instance_repo_cls,
        patch("app.application.invitation_service.SqlCongregationRepository") as cong_repo_cls,
        patch("app.application.invitation_service.SqlInvitationRepository") as inv_repo_cls,
    ):
        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=source_slot)
        slot_repo.save = AsyncMock()
        slot_repo_cls.return_value = slot_repo

        instance_repo = MagicMock()
        instance_repo.get_by_planning_slot = AsyncMock(return_value=source_instance)
        instance_repo.save = AsyncMock()
        instance_repo_cls.return_value = instance_repo

        cong_repo = MagicMock()
        cong_repo.get = AsyncMock(return_value=None)
        cong_repo_cls.return_value = cong_repo

        inv_repo = MagicMock()
        inv_repo.list_by_source_planning_slot = AsyncMock(return_value=[])
        inv_repo_cls.return_value = inv_repo

        targets = [
            InvitationTargetCreate(
                target_type=InvitationTargetType.DISTRICT_CONGREGATION,
                target_congregation_id=target_id,
            ),
        ]

        with pytest.raises(ValueError, match="Target congregation not found"):
            await create_invitations_for_event(
                session,
                source_planning_slot_id=source_slot.id,
                targets=targets,
            )


@pytest.mark.asyncio
async def test_create_invitations_external_note_update_existing():
    """Updates existing EXTERNAL_NOTE invitation when re-inviting."""
    session = MagicMock()
    district_id = uuid.uuid4()
    source_congregation_id = uuid.uuid4()

    source_slot = _planning_slot(
        congregation_id=source_congregation_id, district_id=district_id
    )
    source_instance = _event_instance(source_slot.id)

    existing_inv = CongregationInvitation.create(
        source_event_id=source_slot.id,
        source_planning_slot_id=source_slot.id,
        source_congregation_id=source_congregation_id,
        target_type=InvitationTargetType.EXTERNAL_NOTE,
        external_target_note="Alte Notiz",
    )

    with (
        patch("app.application.invitation_service.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.application.invitation_service.SqlEventInstanceRepository") as instance_repo_cls,
        patch("app.application.invitation_service.SqlCongregationRepository") as cong_repo_cls,
        patch("app.application.invitation_service.SqlInvitationRepository") as inv_repo_cls,
    ):
        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=source_slot)
        slot_repo.save = AsyncMock()
        slot_repo_cls.return_value = slot_repo

        instance_repo = MagicMock()
        instance_repo.get_by_planning_slot = AsyncMock(return_value=source_instance)
        instance_repo.save = AsyncMock()
        instance_repo_cls.return_value = instance_repo

        cong_repo = MagicMock()
        cong_repo_cls.return_value = cong_repo

        inv_repo = MagicMock()
        inv_repo.list_by_source_planning_slot = AsyncMock(return_value=[existing_inv])
        inv_repo.save = AsyncMock()
        inv_repo_cls.return_value = inv_repo

        targets = [
            InvitationTargetCreate(
                target_type=InvitationTargetType.EXTERNAL_NOTE,
                external_target_note="Neue Notiz",
            ),
        ]

        created = await create_invitations_for_event(
            session,
            source_planning_slot_id=source_slot.id,
            targets=targets,
        )

    assert len(created) == 1
    assert created[0].external_target_note == "Neue Notiz"
    inv_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_create_invitations_external_note_create_new():
    """Creates new EXTERNAL_NOTE invitation when no existing one."""
    session = MagicMock()
    district_id = uuid.uuid4()
    source_congregation_id = uuid.uuid4()

    source_slot = _planning_slot(
        congregation_id=source_congregation_id, district_id=district_id
    )
    source_instance = _event_instance(source_slot.id)

    with (
        patch("app.application.invitation_service.SqlPlanningSlotRepository") as slot_repo_cls,
        patch("app.application.invitation_service.SqlEventInstanceRepository") as instance_repo_cls,
        patch("app.application.invitation_service.SqlCongregationRepository") as cong_repo_cls,
        patch("app.application.invitation_service.SqlInvitationRepository") as inv_repo_cls,
    ):
        slot_repo = MagicMock()
        slot_repo.get = AsyncMock(return_value=source_slot)
        slot_repo.save = AsyncMock()
        slot_repo_cls.return_value = slot_repo

        instance_repo = MagicMock()
        instance_repo.get_by_planning_slot = AsyncMock(return_value=source_instance)
        instance_repo.save = AsyncMock()
        instance_repo_cls.return_value = instance_repo

        cong_repo = MagicMock()
        cong_repo_cls.return_value = cong_repo

        inv_repo = MagicMock()
        inv_repo.list_by_source_planning_slot = AsyncMock(return_value=[])  # No existing
        inv_repo.save = AsyncMock()
        inv_repo_cls.return_value = inv_repo

        targets = [
            InvitationTargetCreate(
                target_type=InvitationTargetType.EXTERNAL_NOTE,
                external_target_note="Brand new note",
            ),
        ]

        created = await create_invitations_for_event(
            session,
            source_planning_slot_id=source_slot.id,
            targets=targets,
        )

    assert len(created) == 1
    assert created[0].external_target_note == "Brand new note"
    assert created[0].target_congregation_id is None
    inv_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_sync_linked_invitation_event_schedule_returns_zero():
    """Returns 0 as a no-op placeholder."""
    session = MagicMock()
    source_slot = _planning_slot()

    result = await sync_linked_invitation_event_schedule(
        session, source_slot=source_slot
    )

    assert result == 0
