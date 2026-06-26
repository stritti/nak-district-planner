"""app/application/invitation_service.py: Invitation management service."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.schemas.invitation import InvitationTargetCreate
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.invitation import SqlInvitationRepository
from app.adapters.db.repositories.invitation_overwrite_request import (
    SqlInvitationOverwriteRequestRepository,
)
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationOverwriteRequest,
    InvitationTargetType,
    OverwriteDecisionStatus,
)
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus

logger = logging.getLogger(__name__)


async def create_invitations_for_event(
    session: AsyncSession,
    *,
    source_planning_slot_id: uuid.UUID,
    targets: list[InvitationTargetCreate],
) -> list[CongregationInvitation]:
    """Create invitations for a planning slot and its optional event instance.

    For each DISTRICT_CONGREGATION target, a new PlanningSlot + EventInstance
    is created for the target congregation, linked back to the source via
    invitation_source_congregation_id and invitation_source_event_id.
    """
    slot_repo = SqlPlanningSlotRepository(session)
    event_instance_repo = SqlEventInstanceRepository(session)
    congregation_repo = SqlCongregationRepository(session)
    invitation_repo = SqlInvitationRepository(session)

    source_slot = await slot_repo.get(source_planning_slot_id)
    if source_slot is None:
        raise ValueError("PlanningSlot not found")
    if source_slot.congregation_id is None:
        raise ValueError(
            "Invitations require a source planning slot assigned to a congregation"
        )

    source_event_instance = await event_instance_repo.get_by_planning_slot(
        source_planning_slot_id
    )

    existing = await invitation_repo.list_by_source_planning_slot(source_planning_slot_id)
    existing_by_internal_target = {
        inv.target_congregation_id: inv
        for inv in existing
        if inv.target_type == InvitationTargetType.DISTRICT_CONGREGATION
        and inv.target_congregation_id is not None
    }
    existing_external = next(
        (inv for inv in existing if inv.target_type == InvitationTargetType.EXTERNAL_NOTE),
        None,
    )

    created: list[CongregationInvitation] = []
    for target in targets:
        if target.target_type == InvitationTargetType.DISTRICT_CONGREGATION:
            target_congregation = await congregation_repo.get(target.target_congregation_id)
            if target_congregation is None:
                raise ValueError("Target congregation not found")
            if target_congregation.district_id != source_slot.district_id:
                raise ValueError("Target congregation must belong to source district")

            current = existing_by_internal_target.get(target.target_congregation_id)
            if current is not None:
                current.external_target_note = None
                current.updated_at = datetime.now(UTC)
                await invitation_repo.save(current)
                created.append(current)
                continue

            # Create a PlanningSlot for the target congregation linked back to the source
            target_slot = PlanningSlot.create(
                district_id=source_slot.district_id,
                planning_date=source_slot.planning_date,
                planning_time=source_slot.planning_time,
                congregation_id=target.target_congregation_id,
                category=source_slot.category,
                title=source_slot.title,
                approval_status=source_slot.approval_status,
                invitation_source_congregation_id=source_slot.congregation_id,
                invitation_source_event_id=source_slot.id,
                applicability=list(source_slot.applicability),
            )
            await slot_repo.save(target_slot)

            # Create an EventInstance for the target PlanningSlot
            if source_event_instance is not None:
                target_event_instance = EventInstance.create(
                    planning_slot_id=target_slot.id,
                    title=source_event_instance.title,
                    actual_start_at=source_event_instance.actual_start_at,
                    actual_end_at=source_event_instance.actual_end_at,
                    source=source_event_instance.source,
                    visibility=source_event_instance.visibility,
                    description=source_event_instance.description,
                )
            else:
                # Fallback: derive start/end from PlanningSlot date/time
                start_at = datetime.combine(
                    source_slot.planning_date,
                    source_slot.planning_time,
                    tzinfo=UTC,
                )
                end_at = start_at + timedelta(hours=1)
                target_event_instance = EventInstance.create(
                    planning_slot_id=target_slot.id,
                    title=source_slot.title or "",
                    actual_start_at=start_at,
                    actual_end_at=end_at,
                    source=EventSource.INTERNAL,
                    visibility=EventVisibility.INTERNAL,
                    description=None,
                )
            await event_instance_repo.save(target_event_instance)

            invitation = CongregationInvitation.create(
                source_event_id=source_slot.id,
                source_planning_slot_id=source_slot.id,
                source_congregation_id=source_slot.congregation_id,
                target_type=target.target_type,
                target_congregation_id=target.target_congregation_id,
                external_target_note=None,
                linked_event_id=target_slot.id,
            )
            await invitation_repo.save(invitation)
            created.append(invitation)
            continue

        if existing_external is not None:
            existing_external.external_target_note = target.external_target_note
            existing_external.updated_at = datetime.now(UTC)
            await invitation_repo.save(existing_external)
            created.append(existing_external)
            continue

        invitation = CongregationInvitation.create(
            source_event_id=source_slot.id,
            source_planning_slot_id=source_slot.id,
            source_congregation_id=source_slot.congregation_id,
            target_type=target.target_type,
            target_congregation_id=None,
            external_target_note=target.external_target_note,
            linked_event_id=None,
        )
        await invitation_repo.save(invitation)
        created.append(invitation)

    return created


async def delete_invitation(
    session: AsyncSession,
    *,
    invitation_id: uuid.UUID,
) -> bool:
    """Delete an invitation by its ID.

    Also removes the target PlanningSlot and its EventInstance when the
    invitation has a linked_event_id (created via DISTRICT_CONGREGATION).
    """
    invitation_repo = SqlInvitationRepository(session)
    slot_repo = SqlPlanningSlotRepository(session)
    event_instance_repo = SqlEventInstanceRepository(session)

    invitation = await invitation_repo.get(invitation_id)
    if invitation is None:
        return False

    # Remove the target PlanningSlot + EventInstance that was created for this invitation
    if invitation.linked_event_id is not None:
        target_instance = await event_instance_repo.get_by_planning_slot(
            invitation.linked_event_id
        )
        if target_instance is not None:
            await event_instance_repo.delete(target_instance.id)
        target_slot = await slot_repo.get(invitation.linked_event_id)
        if target_slot is not None:
            await slot_repo.delete(target_slot.id)

    await invitation_repo.delete(invitation.id)
    return True


async def sync_linked_invitation_event_schedule(
    session: AsyncSession,
    *,
    source_slot: PlanningSlot,
) -> int:
    """Sync schedule of invitations linked to a source planning slot.

    Currently a no-op since linked events are no longer created directly.
    Returns 0 to indicate no updates were performed.
    """
    _ = session, source_slot
    return 0


async def propagate_source_event_update(
    session: AsyncSession,
    *,
    source_slot: PlanningSlot,
) -> list[InvitationOverwriteRequest]:
    """Propagate changes from a source planning slot to its invitation targets.

    Logs the propagation attempt and returns the list of pending overwrite
    requests. The actual update logic will be implemented in a follow-up.
    """
    invitation_repo = SqlInvitationRepository(session)
    overwrite_repo = SqlInvitationOverwriteRequestRepository(session)

    invitations = await invitation_repo.list_by_source_planning_slot(source_slot.id)
    if not invitations:
        return []

    existing_open = await overwrite_repo.list_open_by_source_event(source_slot.id)
    logger.info(
        "propagate_source_event_update: planning_slot=%s invitations=%d open_requests=%d",
        source_slot.id,
        len(invitations),
        len(existing_open),
    )
    return []


async def apply_overwrite_decision(
    session: AsyncSession,
    *,
    request_id: uuid.UUID,
    decision: OverwriteDecisionStatus,
) -> InvitationOverwriteRequest | None:
    """Apply a decision (accept/reject) on a pending overwrite request."""
    overwrite_repo = SqlInvitationOverwriteRequestRepository(session)

    request = await overwrite_repo.get(request_id)
    if request is None:
        return None
    if request.status != OverwriteDecisionStatus.PENDING_OVERWRITE:
        return request

    updated = await overwrite_repo.set_status(request.id, decision)
    return updated
