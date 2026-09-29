"""Accept candidates atomically without bypassing district or slot ownership."""

from datetime import UTC, datetime

from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_candidate import CandidateStatus
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus


class CandidateReviewService:
    def __init__(self, candidates, slots, instances, links):
        self.candidates, self.slots, self.instances, self.links = candidates, slots, instances, links

    async def accept(self, candidate, *, user_sub, slot_id=None):
        if candidate.status != CandidateStatus.PENDING:
            raise ValueError("Kandidat wurde bereits geprüft")
        if candidate.end_at < candidate.start_at:
            raise ValueError("Ungültiger Zeitraum")
        if slot_id:
            slot = await self.slots.get(slot_id)
            if slot is None or slot.district_id != candidate.district_id:
                raise ValueError("Termin gehört nicht zum Bezirk")
            if slot.status != PlanningSlotStatus.ACTIVE:
                raise ValueError("Abgesagter Termin kann nicht zugeordnet werden")
        else:
            slot = PlanningSlot.create(
                district_id=candidate.district_id, congregation_id=candidate.congregation_id,
                planning_date=candidate.event_date, planning_time=candidate.event_time,
                title=candidate.title, category=candidate.category,
            )
            await self.slots.save(slot)
        instance = await self.instances.get_by_planning_slot(slot.id)
        if instance and (instance.calendar_integration_id or instance.sync_state != SyncState.CLEAN):
            raise ValueError("Termin ist bereits verknüpft oder hat ungeklärte Änderungen")
        if instance is None:
            instance = EventInstance.create(
                planning_slot_id=slot.id, title=candidate.title,
                actual_start_at=candidate.start_at, actual_end_at=candidate.end_at,
                source=EventSource.EXTERNAL, visibility=EventVisibility.PUBLIC,
            )
        instance.title, instance.description = candidate.title, candidate.description
        instance.actual_start_at, instance.actual_end_at = candidate.start_at, candidate.end_at
        instance.calendar_integration_id = candidate.calendar_integration_id
        instance.external_uid, instance.content_hash = candidate.external_event_id, candidate.content_hash
        instance.source = EventSource.EXTERNAL
        instance.deviation_flag = candidate.start_at != datetime.combine(slot.planning_date, slot.planning_time, tzinfo=UTC)
        instance.updated_at = instance.last_external_modified_at = datetime.now(UTC)
        await self.instances.save(instance)
        await self.links.save(ExternalEventLink.create(
            event_instance_id=instance.id, provider=candidate.source,
            external_event_id=candidate.external_event_id,
            calendar_integration_id=candidate.calendar_integration_id,
            last_synced_hash=candidate.content_hash,
        ))
        candidate.review(CandidateStatus.ACCEPTED, user_sub, slot.id)
        await self.candidates.save(candidate)
        return candidate

    async def dismiss(self, candidate, *, user_sub):
        candidate.review(CandidateStatus.DISMISSED, user_sub)
        await self.candidates.save(candidate)
        return candidate
