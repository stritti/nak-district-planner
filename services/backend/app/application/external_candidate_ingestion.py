"""Governance-safe ingestion of new external calendar events.

Existing mapped events remain owned by the hardened sync state machine.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.domain.models.event_instance import EventInstance, SyncState
from app.domain.models.external_event_candidate import CandidateStatus, ExternalEventCandidate
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.notification import Notification, NotificationType
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.services.external_event_mapping import (
    ExternalEventMappingData,
    apply_external_event_to_instance,
    create_external_event_link,
)

logger = logging.getLogger(__name__)


class CandidateRepository(Protocol):
    async def by_external_event(self, integration_id, external_id): ...
    async def save(self, candidate: ExternalEventCandidate) -> None: ...


class InstanceRepository(Protocol):
    async def get_by_planning_slot(self, slot_id) -> EventInstance | None: ...
    async def save(self, instance: EventInstance) -> None: ...


class LinkRepository(Protocol):
    async def save(self, link: ExternalEventLink) -> None: ...


class NotificationRepository(Protocol):
    async def save(self, notification: Notification) -> None: ...


async def find_exact_matching_slot(
    *, session: AsyncSession, district_id, congregation_id,
    event_start, event_category,
) -> PlanningSlot | None:
    """Only an active, exact UTC date/time and category-compatible slot is eligible."""
    instant = event_start.astimezone(UTC)
    slots = await SqlPlanningSlotRepository(session).list_for_date_range(
        district_id=district_id, from_date=instant.date(), to_date=instant.date()
    )
    for slot in slots:
        if slot.status != PlanningSlotStatus.ACTIVE:
            continue
        if slot.congregation_id != congregation_id:
            continue
        if event_category is not None and slot.category not in (None, event_category):
            continue
        if slot.planning_time.replace(tzinfo=None) != instant.time().replace(tzinfo=None):
            continue
        return slot
    return None


async def ingest_unlinked_event(
    *, raw: RawCalendarEvent, integration, session: AsyncSession,
    candidate_repo: CandidateRepository, instance_repo: InstanceRepository,
    link_repo: LinkRepository, notification_repo: NotificationRepository,
    content_hash: str,
) -> bool:
    """Process an unlinked event. Returns true only for an accepted exact auto-match.

    An unassignable event never creates a PlanningSlot without review. The
    integration transaction serializes duplicate deliveries and owns all writes.
    """
    candidate = await candidate_repo.by_external_event(integration.id, raw.uid)
    if raw.is_cancelled:
        if candidate is not None and candidate.status == CandidateStatus.PENDING:
            candidate.refresh(raw, content_hash, integration.default_category)
            candidate.review(CandidateStatus.DISMISSED, None)
            await candidate_repo.save(candidate)
        return False
    if raw.end_at <= raw.start_at:
        # Never persist invalid candidate intervals or partially map bad input.
        logger.warning("External candidate event skipped because its interval is invalid")
        return False

    slot = await find_exact_matching_slot(
        session=session, district_id=integration.district_id,
        congregation_id=integration.congregation_id,
        event_start=raw.start_at, event_category=integration.default_category,
    )
    if slot is not None:
        instance = await instance_repo.get_by_planning_slot(slot.id)
        # Even the same integration must not claim a different already mapped UID.
        assignable = instance is None or (
            instance.calendar_integration_id is None and instance.sync_state == SyncState.CLEAN
        )
        if assignable:
            data = ExternalEventMappingData(
                title=raw.title, description=raw.description,
                start_at=raw.start_at, end_at=raw.end_at,
                external_event_id=raw.uid, provider=integration.type.value,
                calendar_integration_id=integration.id,
                content_hash=content_hash, revision_marker=raw.revision_marker,
                provider_resource_id=raw.resource_id,
            )
            mapped = apply_external_event_to_instance(slot=slot, instance=instance, data=data)
            await instance_repo.save(mapped)
            await link_repo.save(create_external_event_link(event_instance_id=mapped.id, data=data))
            if candidate is not None and candidate.status == CandidateStatus.PENDING:
                candidate.review(CandidateStatus.ACCEPTED, None, slot.id)
                await candidate_repo.save(candidate)
            return True

    if candidate is None:
        candidate = ExternalEventCandidate.create(
            integration=integration, raw=raw, content_hash=content_hash
        )
        await candidate_repo.save(candidate)
        await notification_repo.save(
            Notification.create(
                district_id=integration.district_id,
                type=NotificationType.CANDIDATE_REVIEW,
                title="Externer Termin benötigt Prüfung",
                body=raw.title,
                congregation_id=integration.congregation_id,
                payload={"candidate_id": str(candidate.id)},
            )
        )
        logger.info("External candidate created candidate_id=%s", candidate.id)
    elif candidate.status == CandidateStatus.PENDING:
        candidate.refresh(raw, content_hash, integration.default_category)
        await candidate_repo.save(candidate)
    return False
