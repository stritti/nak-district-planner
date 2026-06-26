"""app/application/invitation_service.py: Module."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.api.schemas.invitation import InvitationTargetCreate
from app.adapters.db.repositories.congregation import SqlCongregationRepository
from app.adapters.db.repositories.invitation import SqlInvitationRepository
from app.adapters.db.repositories.invitation_overwrite_request import (
    SqlInvitationOverwriteRequestRepository,
)
# TODO: remove Event/EventStatus imports — will be refactored for Event-free architecture
from app.domain.models.invitation import (
    CongregationInvitation,
    InvitationOverwriteRequest,
    InvitationTargetType,
    OverwriteDecisionStatus,
)


async def create_invitations_for_event(
    session: AsyncSession,
    *,
    source_event_id,
    targets: list[InvitationTargetCreate],
) -> list[CongregationInvitation]:
    event_repo = None  # TODO: refactor to PlanningSlotRepository
    congregation_repo = SqlCongregationRepository(session)
    invitation_repo = SqlInvitationRepository(session)

    source_event = None  # TODO: refactor to PlanningSlotRepository
    if source_event is None:
        raise ValueError("Event not found")
    if source_event.congregation_id is None:
        raise ValueError("Invitations require a source event assigned to a congregation")

    existing = await invitation_repo.list_by_source_event(source_event.id)
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
            if target_congregation.district_id != source_event.district_id:
                raise ValueError("Target congregation must belong to source district")

            current = existing_by_internal_target.get(target.target_congregation_id)
            if current is not None:
                current.external_target_note = None
                current.updated_at = datetime.now(UTC)
                await invitation_repo.save(current)
                created.append(current)
                continue

            # TODO: refactor for Event-free architecture
            # linked_event = Event.create(
            #     title=source_event.title,
            #     description=source_event.description,
            #     start_at=source_event.start_at,
            #     end_at=source_event.end_at,
            #     district_id=source_event.district_id,
            #     congregation_id=target.target_congregation_id,
            #     category=source_event.category,
            #     source=source_event.source,
            #     status=source_event.status,
            #     visibility=source_event.visibility,
            #     audiences=list(source_event.audiences),
            #     applicability=list(source_event.applicability),
            #     invitation_source_congregation_id=source_event.congregation_id,
            #     invitation_source_event_id=source_event.id,
            # )
            # await event_repo.save(linked_event)
            # Placeholder for linked_event — will be refactored
            invitation = CongregationInvitation.create(
                source_event_id=source_event.id,
                source_congregation_id=source_event.congregation_id,
                target_type=target.target_type,
                target_congregation_id=target.target_congregation_id,
                external_target_note=None,
                linked_event_id=None,  # TODO: linked_event will be removed
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
            source_event_id=source_event.id,
            source_congregation_id=source_event.congregation_id,
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
    invitation_id,
) -> bool:
    invitation_repo = SqlInvitationRepository(session)

    invitation = await invitation_repo.get(invitation_id)
    if invitation is None:
        return False

    if invitation.linked_event_id is not None:
        # TODO: refactor for Event-free architecture — EventRepository removed
        pass

    await invitation_repo.delete(invitation.id)
    return True


async def sync_linked_invitation_event_schedule(
    session: AsyncSession,
    *,
    source_event: object,  # TODO: refactor for Event-free architecture
) -> int:
    # TODO: refactor for Event-free architecture — EventRepository removed
    return 0


async def propagate_source_event_update(
    session: AsyncSession,
    *,
    source_event: object,  # TODO: refactor for Event-free architecture
) -> list[InvitationOverwriteRequest]:
    invitation_repo = SqlInvitationRepository(session)
    overwrite_repo = SqlInvitationOverwriteRequestRepository(session)

    invitations = await invitation_repo.list_by_source_event(source_event.id)
    if not invitations:
        return []

    existing_open = await overwrite_repo.list_open_by_source_event(source_event.id)

    # TODO: refactor for Event-free architecture — EventRepository removed
    return []


async def apply_overwrite_decision(
    session: AsyncSession,
    *,
    request_id,
    decision: OverwriteDecisionStatus,
) -> InvitationOverwriteRequest | None:
    overwrite_repo = SqlInvitationOverwriteRequestRepository(session)

    request = await overwrite_repo.get(request_id)
    if request is None:
        return None
    if request.status != OverwriteDecisionStatus.PENDING_OVERWRITE:
        return request

    # TODO: refactor to PlanningSlotRepository — event update removed

    updated = await overwrite_repo.set_status(request.id, decision)
    return updated
