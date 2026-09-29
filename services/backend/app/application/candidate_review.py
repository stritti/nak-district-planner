"""Candidate review application service."""

from __future__ import annotations

import logging

from typing import Protocol
from uuid import UUID

from app.domain.errors import (
    CandidateAlreadyReviewed,
    CandidateInvalidPeriod,
    CandidateSlotAlreadyLinked,
    CandidateSlotNotAssignable,
)
from app.domain.models.event_instance import EventInstance, SyncState
from app.domain.models.external_event_candidate import CandidateStatus, ExternalEventCandidate
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.services.external_event_mapping import (
    ExternalEventMappingData,
    apply_external_event_to_instance,
    create_external_event_link,
)


logger = logging.getLogger(__name__)


class CandidateRepository(Protocol):
    async def save(self, candidate: ExternalEventCandidate) -> None: ...


class PlanningSlotRepository(Protocol):
    async def get(self, slot_id: UUID) -> PlanningSlot | None: ...
    async def save(self, slot: PlanningSlot) -> None: ...


class EventInstanceRepository(Protocol):
    async def get_by_planning_slot(self, planning_slot_id: UUID) -> EventInstance | None: ...
    async def save(self, instance: EventInstance) -> None: ...


class ExternalEventLinkRepository(Protocol):
    async def save(self, link: ExternalEventLink) -> None: ...


class CandidateReviewService:
    def __init__(
        self,
        *,
        candidates: CandidateRepository,
        slots: PlanningSlotRepository,
        instances: EventInstanceRepository,
        links: ExternalEventLinkRepository,
    ) -> None:
        self.candidates = candidates
        self.slots = slots
        self.instances = instances
        self.links = links

    async def accept(
        self,
        candidate: ExternalEventCandidate,
        *,
        user_sub: str,
        slot_id: UUID | None = None,
    ) -> ExternalEventCandidate:
        if candidate.status != CandidateStatus.PENDING:
            raise CandidateAlreadyReviewed("Kandidat wurde bereits geprüft")
        if candidate.end_at < candidate.start_at:
            raise CandidateInvalidPeriod("Ungültiger Zeitraum")

        slot = await self._resolve_slot(candidate, slot_id)
        instance = await self.instances.get_by_planning_slot(slot.id)
        if instance and (
            instance.calendar_integration_id is not None
            or instance.sync_state != SyncState.CLEAN
        ):
            raise CandidateSlotAlreadyLinked(
                "Termin ist bereits verknüpft oder hat ungeklärte Änderungen"
            )

        data = ExternalEventMappingData(
            title=candidate.title,
            description=candidate.description,
            start_at=candidate.start_at,
            end_at=candidate.end_at,
            external_event_id=candidate.external_event_id,
            provider=candidate.source,
            calendar_integration_id=candidate.calendar_integration_id,
            content_hash=candidate.content_hash,
        )
        mapped_instance = apply_external_event_to_instance(
            slot=slot,
            instance=instance,
            data=data,
        )
        await self.instances.save(mapped_instance)
        await self.links.save(
            create_external_event_link(
                event_instance_id=mapped_instance.id,
                data=data,
            )
        )
        candidate.review(CandidateStatus.ACCEPTED, user_sub, slot.id)
        await self.candidates.save(candidate)
        logger.info(
            "External event candidate accepted candidate_id=%s district_id=%s slot_id=%s reviewer=%s",
            candidate.id,
            candidate.district_id,
            slot.id,
            user_sub,
        )
        return candidate

    async def dismiss(
        self,
        candidate: ExternalEventCandidate,
        *,
        user_sub: str,
    ) -> ExternalEventCandidate:
        candidate.review(CandidateStatus.DISMISSED, user_sub)
        await self.candidates.save(candidate)
        logger.info(
            "External event candidate dismissed candidate_id=%s district_id=%s reviewer=%s",
            candidate.id,
            candidate.district_id,
            user_sub,
        )
        return candidate

    async def _resolve_slot(
        self,
        candidate: ExternalEventCandidate,
        slot_id: UUID | None,
    ) -> PlanningSlot:
        if slot_id is None:
            slot = PlanningSlot.create(
                district_id=candidate.district_id,
                congregation_id=candidate.congregation_id,
                planning_date=candidate.event_date,
                planning_time=candidate.event_time,
                title=candidate.title,
                category=candidate.category,
            )
            await self.slots.save(slot)
            return slot

        slot = await self.slots.get(slot_id)
        if slot is None or slot.district_id != candidate.district_id:
            raise CandidateSlotNotAssignable("Termin gehört nicht zum Bezirk")
        if slot.status != PlanningSlotStatus.ACTIVE:
            raise CandidateSlotNotAssignable(
                "Abgesagter Termin kann nicht zugeordnet werden"
            )
        return slot
