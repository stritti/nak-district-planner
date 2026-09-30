"""Shared mapping rules for automatic ingestion and explicit candidate approval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.config import settings
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.planning_slot import PlanningSlot


@dataclass(frozen=True)
class ExternalEventMappingData:
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    external_event_id: str
    provider: str
    calendar_integration_id: UUID
    content_hash: str
    revision_marker: str | None = None
    provider_resource_id: str | None = None


def has_significant_deviation(slot: PlanningSlot, event_start: datetime, event_end: datetime) -> bool:
    """Check both start and planned-duration/end deviations."""
    planned_start = datetime.combine(slot.planning_date, slot.planning_time, tzinfo=UTC)
    planned_end = planned_start + timedelta(minutes=settings.sync_expected_duration_minutes)
    return (
        abs((event_start - planned_start).total_seconds()) > 300
        or abs((event_end - planned_end).total_seconds()) > 300
    )


def apply_external_event_to_instance(
    *, slot: PlanningSlot, instance: EventInstance | None, data: ExternalEventMappingData
) -> EventInstance:
    """Map a validated external event without modifying the structural planning slot."""
    if instance is None:
        instance = EventInstance.create(
            planning_slot_id=slot.id, title=data.title, actual_start_at=data.start_at,
            actual_end_at=data.end_at, description=data.description,
            source=EventSource.EXTERNAL, visibility=EventVisibility.PUBLIC,
        )
    now = datetime.now(UTC)
    instance.title = data.title
    instance.description = data.description
    instance.actual_start_at = data.start_at
    instance.actual_end_at = data.end_at
    instance.source = EventSource.EXTERNAL
    instance.sync_state = SyncState.CLEAN
    instance.content_hash = data.content_hash
    instance.external_uid = data.external_event_id
    instance.calendar_integration_id = data.calendar_integration_id
    instance.last_external_modified_at = now
    instance.deviation_flag = has_significant_deviation(slot, data.start_at, data.end_at)
    instance.updated_at = now
    return instance


def create_external_event_link(*, event_instance_id: UUID, data: ExternalEventMappingData) -> ExternalEventLink:
    """Preserve revision, resource identity and field baseline for #375 conflict handling."""
    return ExternalEventLink.create(
        event_instance_id=event_instance_id, provider=data.provider,
        external_event_id=data.external_event_id,
        calendar_integration_id=data.calendar_integration_id,
        last_synced_hash=data.content_hash, revision_marker=data.revision_marker,
        last_synced_payload={
            "title": data.title,
            "description": data.description,
            "actual_start_at": data.start_at.isoformat(),
            "actual_end_at": data.end_at.isoformat(),
        },
        provider_resource_id=data.provider_resource_id,
    )
