"""Calendar sync service — UC-02, hardened for M3 with governed ingestion.

Existing linked events follow the #375 sync state machine. New events are
matched only when governance-safe; otherwise they become review candidates.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections import Counter
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.google_connector import GoogleCalendarConnector
from app.adapters.calendar.ical_connector import ICalConnector
from app.adapters.calendar.microsoft_connector import MicrosoftGraphCalendarConnector
from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.external_event_link import SqlExternalEventLinkRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.application.crypto import decrypt_credentials
from app.application.external_candidate_sync_adapter import import_candidate_or_match
from app.config import settings
from app.domain.errors import IntegrationNotFoundError
from app.domain.models.calendar_integration import (
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
    SyncDeleteMode,
)
from app.domain.models.event_instance import EventInstance, EventSource, SyncState
from app.domain.models.external_event_link import ExternalEventLink, ExternalEventLinkState
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError
from app.domain.services.sync_policy import (
    INTERNAL_DELETE_MARKER,
    SyncFieldAuthority,
    classify_field,
    inbound_state,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncContext:
    """Runtime dependencies for one integration sync run."""

    integration_id: uuid.UUID
    session: AsyncSession
    integration: CalendarIntegration
    connector: CalendarConnector
    credentials: dict
    instance_repo: SqlEventInstanceRepository
    slot_repo: SqlPlanningSlotRepository
    link_repo: SqlExternalEventLinkRepository


@dataclass
class SyncResult:
    """Result of a calendar sync operation."""

    created: int = 0
    updated: int = 0
    cancelled: int = 0
    auto_matched: int = 0
    skipped: int = 0
    failed: int = 0


_CONNECTOR_MAP: dict[CalendarType, type[CalendarConnector]] = {
    CalendarType.ICS: ICalConnector,
    CalendarType.GOOGLE: GoogleCalendarConnector,
    CalendarType.MICROSOFT: MicrosoftGraphCalendarConnector,
    CalendarType.CALDAV: CalDAVConnector,
}


def _get_connector(calendar_type: CalendarType) -> CalendarConnector:
    connector_cls = _CONNECTOR_MAP.get(calendar_type)
    if connector_cls is None:
        raise NotImplementedError(f"No connector implemented for {calendar_type}")
    return connector_cls()


def _compute_content_hash(raw_event: RawCalendarEvent) -> str:
    """Compute deterministic SHA-256 hash for external event change detection."""
    raw_str = (
        f"{raw_event.uid}|{raw_event.start_at}|{raw_event.end_at}"
        f"|{raw_event.title}|{raw_event.description}|{raw_event.is_cancelled}"
    )
    return hashlib.sha256(raw_str.encode()).hexdigest()


def _has_significant_deviation(
    slot: PlanningSlot, event_start: datetime, event_end: datetime
) -> bool:
    """Check start or end deviation against the planned expected interval."""
    planned_start = datetime.combine(slot.planning_date, slot.planning_time, tzinfo=UTC)
    planned_end = planned_start + timedelta(minutes=settings.sync_expected_duration_minutes)
    return (
        abs((event_start - planned_start).total_seconds()) > 300
        or abs((event_end - planned_end).total_seconds()) > 300
    )


class SyncOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    CANCELLED = "cancelled"
    AUTO_MATCHED = "auto_matched"
    SKIPPED = "skipped"
    FAILED = "failed"


def _sync_payload(raw: RawCalendarEvent) -> dict[str, str | None]:
    return {
        "title": raw.title,
        "description": raw.description,
        "actual_start_at": raw.start_at.isoformat(),
        "actual_end_at": raw.end_at.isoformat(),
    }


def _instance_payload(instance: EventInstance) -> dict[str, str | None]:
    return {
        "title": instance.title,
        "description": instance.description,
        "actual_start_at": instance.actual_start_at.isoformat(),
        "actual_end_at": instance.actual_end_at.isoformat(),
    }


def _changed_fields(
    current: dict[str, str | None], baseline: dict[str, str | None] | None
) -> set[str]:
    if baseline is None:
        return set(current)
    return {field for field, value in current.items() if baseline.get(field) != value}


async def _import_new_event(
    *, raw: RawCalendarEvent, context: SyncContext, new_content_hash: str
) -> SyncOutcome:
    """Apply governance to an event without an existing external mapping."""
    matched = await import_candidate_or_match(
        raw=raw, context=context, new_content_hash=new_content_hash
    )
    return SyncOutcome.AUTO_MATCHED if matched else SyncOutcome.SKIPPED


async def _push_internal_delete(
    *,
    context: SyncContext,
    raw: RawCalendarEvent,
    existing_link: ExternalEventLink,
    instance: EventInstance,
    new_content_hash: str,
) -> None:
    """Push an internal cancellation to the provider exactly once."""
    await context.connector.delete_event(context.credentials, raw)
    now = datetime.now(UTC)
    existing_link.revision_marker = INTERNAL_DELETE_MARKER
    existing_link.last_synced_hash = new_content_hash
    existing_link.state = ExternalEventLinkState.SYNC_TOMBSTONE
    existing_link.deletion_origin = "INTERNAL"
    existing_link.deletion_reason = "local-cancellation-pushed"
    existing_link.tombstoned_at = now
    existing_link.updated_at = now
    await context.link_repo.save(existing_link)
    instance.sync_state = SyncState.CLEAN
    await context.instance_repo.save(instance)


async def _handle_external_cancel(
    *,
    context: SyncContext,
    raw: RawCalendarEvent,
    existing_link: ExternalEventLink,
    instance: EventInstance,
    slot: PlanningSlot | None,
    new_content_hash: str,
) -> SyncOutcome:
    """Apply an external cancellation according to the configured delete mode."""
    if instance.sync_state in (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT):
        instance.sync_state = SyncState.CONFLICT
        await context.instance_repo.save(instance)
        return SyncOutcome.SKIPPED
    if slot and context.integration.delete_behavior == SyncDeleteMode.HARD_DELETE:
        now = datetime.now(UTC)
        existing_link.event_instance_id = None
        existing_link.last_synced_hash = new_content_hash
        existing_link.last_synced_payload = _sync_payload(raw)
        existing_link.state = ExternalEventLinkState.SYNC_TOMBSTONE
        existing_link.deletion_origin = "EXTERNAL"
        existing_link.deletion_reason = "provider-cancellation"
        existing_link.tombstoned_at = now
        existing_link.updated_at = now
        await context.link_repo.save(existing_link)
        await context.slot_repo.delete(slot.id)
        return SyncOutcome.CANCELLED
    if slot and slot.status != PlanningSlotStatus.CANCELLED:
        slot.status = PlanningSlotStatus.CANCELLED
        slot.updated_at = datetime.now(UTC)
        await context.slot_repo.save(slot)
        existing_link.last_synced_hash = new_content_hash
        existing_link.last_synced_payload = _sync_payload(raw)
        existing_link.revision_marker = raw.revision_marker
        existing_link.updated_at = datetime.now(UTC)
        await context.link_repo.save(existing_link)
        return SyncOutcome.CANCELLED
    existing_link.last_synced_hash = new_content_hash
    existing_link.last_synced_payload = _sync_payload(raw)
    existing_link.revision_marker = raw.revision_marker
    existing_link.updated_at = datetime.now(UTC)
    await context.link_repo.save(existing_link)
    return SyncOutcome.SKIPPED


async def _apply_external_update(
    *,
    context: SyncContext,
    raw: RawCalendarEvent,
    existing_link: ExternalEventLink,
    instance: EventInstance,
    slot: PlanningSlot | None,
    new_content_hash: str,
) -> SyncOutcome:
    """Route incoming fields by authority and advance the sync state machine."""
    incoming_payload = _sync_payload(raw)
    if instance.sync_state in (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT):
        external_changed = _changed_fields(incoming_payload, existing_link.last_synced_payload)
        internal_changed = _changed_fields(_instance_payload(instance), existing_link.last_synced_payload)
        overlapping = external_changed & internal_changed
        unsafe = {
            field for field in external_changed
            if classify_field(field) != SyncFieldAuthority.SOFT
        }
        if existing_link.last_synced_payload is None or overlapping or unsafe:
            instance.sync_state = SyncState.CONFLICT
            await context.instance_repo.save(instance)
            return SyncOutcome.SKIPPED
        next_state = SyncState.DIRTY_INTERNAL
        fields_to_apply = external_changed
    else:
        next_state = inbound_state(instance.sync_state, changed=True)
        fields_to_apply = set(incoming_payload)
    incoming = {
        "title": raw.title,
        "actual_start_at": raw.start_at,
        "actual_end_at": raw.end_at,
        "description": raw.description,
    }
    for field, value in incoming.items():
        if field in fields_to_apply and classify_field(field) != SyncFieldAuthority.STRUCTURAL:
            setattr(instance, field, value)
    instance.source = EventSource.EXTERNAL
    instance.sync_state = next_state
    if slot:
        instance.deviation_flag = _has_significant_deviation(slot, raw.start_at, raw.end_at)
    instance.content_hash = new_content_hash
    instance.last_external_modified_at = datetime.now(UTC)
    instance.updated_at = datetime.now(UTC)
    await context.instance_repo.save(instance)
    existing_link.last_synced_hash = new_content_hash
    existing_link.last_synced_payload = incoming_payload
    existing_link.revision_marker = raw.revision_marker
    existing_link.updated_at = datetime.now(UTC)
    await context.link_repo.save(existing_link)
    return SyncOutcome.UPDATED


async def _process_existing_event(
    *,
    raw: RawCalendarEvent,
    context: SyncContext,
    existing_link: ExternalEventLink,
    new_content_hash: str,
) -> SyncOutcome:
    """Handle a raw event with an existing ExternalEventLink."""
    if existing_link.state == ExternalEventLinkState.SYNC_TOMBSTONE:
        return SyncOutcome.SKIPPED
    if existing_link.event_instance_id is None:
        return SyncOutcome.SKIPPED
    instance = await context.instance_repo.get(existing_link.event_instance_id)
    if instance is None:
        return SyncOutcome.SKIPPED
    slot = await context.slot_repo.get(instance.planning_slot_id)
    if (
        instance.sync_state == SyncState.DIRTY_INTERNAL
        and not instance.deviation_flag
        and (raw.start_at != instance.actual_start_at or raw.end_at != instance.actual_end_at)
        and CalendarCapability.WRITE in context.integration.capabilities
        and existing_link.last_synced_hash == new_content_hash
    ):
        revision = await context.connector.update_event_times(
            context.credentials, raw,
            start_at=instance.actual_start_at,
            end_at=instance.actual_end_at,
        )
        acknowledged = replace(
            raw, start_at=instance.actual_start_at, end_at=instance.actual_end_at,
            revision_marker=revision or raw.revision_marker,
        )
        existing_link.last_synced_hash = _compute_content_hash(acknowledged)
        existing_link.last_synced_payload = _sync_payload(acknowledged)
        existing_link.revision_marker = acknowledged.revision_marker
        existing_link.updated_at = datetime.now(UTC)
        instance.sync_state = SyncState.CLEAN
        await context.link_repo.save(existing_link)
        await context.instance_repo.save(instance)
        return SyncOutcome.UPDATED
    if (
        slot and slot.status == PlanningSlotStatus.CANCELLED
        and instance.sync_state == SyncState.DIRTY_INTERNAL
        and CalendarCapability.WRITE in context.integration.capabilities
    ):
        if existing_link.last_synced_hash != new_content_hash:
            instance.sync_state = SyncState.CONFLICT
            await context.instance_repo.save(instance)
            return SyncOutcome.SKIPPED
        await _push_internal_delete(
            context=context, raw=raw, existing_link=existing_link,
            instance=instance, new_content_hash=new_content_hash,
        )
        return SyncOutcome.CANCELLED
    if existing_link.last_synced_hash == new_content_hash:
        return SyncOutcome.SKIPPED
    if raw.is_cancelled:
        return await _handle_external_cancel(
            context=context, raw=raw, existing_link=existing_link,
            instance=instance, slot=slot, new_content_hash=new_content_hash,
        )
    return await _apply_external_update(
        context=context, raw=raw, existing_link=existing_link,
        instance=instance, slot=slot, new_content_hash=new_content_hash,
    )


async def _reconcile_missing_provider_events(
    *, context: SyncContext, seen_uids: set[str], cutoff: datetime
) -> Counter[SyncOutcome]:
    """Reconcile links absent from a complete authoritative provider window."""
    outcomes: Counter[SyncOutcome] = Counter()
    for link in await context.link_repo.list_active_by_integration(context.integration_id):
        if link.external_event_id in seen_uids or link.event_instance_id is None:
            continue
        instance = await context.instance_repo.get(link.event_instance_id)
        if instance is None or instance.actual_end_at < cutoff:
            continue
        slot = await context.slot_repo.get(instance.planning_slot_id)
        if instance.sync_state in (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT):
            instance.sync_state = SyncState.CONFLICT
            await context.instance_repo.save(instance)
            outcomes[SyncOutcome.SKIPPED] += 1
            continue
        now = datetime.now(UTC)
        if slot and context.integration.delete_behavior == SyncDeleteMode.HARD_DELETE:
            link.event_instance_id = None
            link.state = ExternalEventLinkState.SYNC_TOMBSTONE
            link.deletion_origin = "EXTERNAL"
            link.deletion_reason = "missing-from-authoritative-snapshot"
            link.tombstoned_at = now
            link.updated_at = now
            await context.link_repo.save(link)
            await context.slot_repo.delete(slot.id)
            outcomes[SyncOutcome.CANCELLED] += 1
        elif slot and slot.status != PlanningSlotStatus.CANCELLED:
            slot.status = PlanningSlotStatus.CANCELLED
            slot.updated_at = now
            link.updated_at = now
            await context.slot_repo.save(slot)
            await context.link_repo.save(link)
            outcomes[SyncOutcome.CANCELLED] += 1
    return outcomes


async def push_deviation_resolution(instance: EventInstance, session: AsyncSession) -> bool:
    """Push resolved times immediately to writable provider links."""
    link_repo = SqlExternalEventLinkRepository(session)
    integration_repo = SqlCalendarIntegrationRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    pushed = False
    for link in await link_repo.list_by_event_instance(instance.id):
        if link.state != ExternalEventLinkState.ACTIVE:
            continue
        integration = await integration_repo.get(link.calendar_integration_id)
        if integration is None or CalendarCapability.WRITE not in integration.capabilities:
            continue
        raw = RawCalendarEvent(
            uid=link.external_event_id,
            title=instance.title,
            start_at=instance.actual_start_at,
            end_at=instance.actual_end_at,
            description=instance.description,
            content_hash="",
            is_cancelled=False,
            revision_marker=link.revision_marker,
            resource_id=link.provider_resource_id,
        )
        connector = _get_connector(integration.type)
        revision = await connector.update_event_times(
            decrypt_credentials(integration.credentials_enc), raw,
            start_at=instance.actual_start_at, end_at=instance.actual_end_at,
        )
        acknowledged = replace(raw, revision_marker=revision or raw.revision_marker)
        link.last_synced_hash = _compute_content_hash(acknowledged)
        link.last_synced_payload = _sync_payload(acknowledged)
        link.revision_marker = acknowledged.revision_marker
        link.updated_at = datetime.now(UTC)
        await link_repo.save(link)
        pushed = True
    if pushed and instance.sync_state == SyncState.DIRTY_INTERNAL:
        instance.sync_state = SyncState.CLEAN
        await instance_repo.save(instance)
    return pushed


async def push_conflict_resolution(instance: EventInstance, session: AsyncSession) -> bool:
    """Push a resolvable conflict in favour of internal planning data.

    The connector port currently guarantees writes for event times only. Text
    fields must therefore never be acknowledged as synchronized when they
    changed internally. Explicit conflict resolution intentionally omits the
    stale provider revision so a time conflict can be overwritten by the
    planner's decision; the returned provider revision becomes the new
    acknowledgement baseline.
    """
    link_repo = SqlExternalEventLinkRepository(session)
    integration_repo = SqlCalendarIntegrationRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    writable_links: list[tuple[ExternalEventLink, CalendarIntegration]] = []
    internal_payload = _instance_payload(instance)

    for link in await link_repo.list_by_event_instance(instance.id):
        if link.state != ExternalEventLinkState.ACTIVE:
            continue
        integration = await integration_repo.get(link.calendar_integration_id)
        if integration is None or CalendarCapability.WRITE not in integration.capabilities:
            continue
        changed_fields = _changed_fields(internal_payload, link.last_synced_payload)
        unsupported_fields = changed_fields - {"actual_start_at", "actual_end_at"}
        if unsupported_fields:
            fields = ", ".join(sorted(unsupported_fields))
            raise CalendarConnectorError(
                f"Konflikt enthält nicht schreibbare Felder: {fields}"
            )
        writable_links.append((link, integration))

    pushed = False
    for link, integration in writable_links:
        raw = RawCalendarEvent(
            uid=link.external_event_id,
            title=instance.title,
            start_at=instance.actual_start_at,
            end_at=instance.actual_end_at,
            description=instance.description,
            content_hash="",
            is_cancelled=False,
            revision_marker=None,
            resource_id=link.provider_resource_id,
        )
        connector = _get_connector(integration.type)
        revision = await connector.update_event_times(
            decrypt_credentials(integration.credentials_enc), raw,
            start_at=instance.actual_start_at, end_at=instance.actual_end_at,
        )
        acknowledged = replace(raw, revision_marker=revision)
        link.last_synced_hash = _compute_content_hash(acknowledged)
        link.last_synced_payload = _sync_payload(acknowledged)
        link.revision_marker = revision
        link.updated_at = datetime.now(UTC)
        await link_repo.save(link)
        pushed = True
    if pushed:
        instance.sync_state = SyncState.CLEAN
        await instance_repo.save(instance)
    return pushed


async def run_sync(integration_id: uuid.UUID, session: AsyncSession) -> SyncResult:
    """Sync one CalendarIntegration. Return successful, skipped and failed counts."""
    lock_key = int.from_bytes(integration_id.bytes[:8], "big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    integration_repo = SqlCalendarIntegrationRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    slot_repo = SqlPlanningSlotRepository(session)
    link_repo = SqlExternalEventLinkRepository(session)
    integration = await integration_repo.get(integration_id)
    if integration is None:
        raise IntegrationNotFoundError(f"CalendarIntegration {integration_id} not found")
    counters: Counter[SyncOutcome] = Counter()
    try:
        credentials = decrypt_credentials(integration.credentials_enc)
        connector = _get_connector(integration.type)
        context = SyncContext(
            integration_id=integration_id, session=session, integration=integration,
            connector=connector, credentials=credentials,
            instance_repo=instance_repo, slot_repo=slot_repo, link_repo=link_repo,
        )
        cutoff = datetime.now(UTC) - timedelta(days=62)
        raw_events = await connector.fetch_events(credentials, from_dt=cutoff)
        seen_uids: set[str] = set()
        for raw in raw_events:
            seen_uids.add(raw.uid)
            existing_link = await link_repo.get_by_external_event(
                provider=context.integration.type.value,
                external_event_id=raw.uid,
                calendar_integration_id=context.integration_id,
            )
            new_content_hash = _compute_content_hash(raw)
            try:
                if existing_link is None:
                    outcome = await _import_new_event(
                        raw=raw, context=context,
                        new_content_hash=new_content_hash,
                    )
                else:
                    outcome = await _process_existing_event(
                        raw=raw, context=context, existing_link=existing_link,
                        new_content_hash=new_content_hash,
                    )
                counters[outcome] += 1
            except CalendarConnectorError:
                # Never include provider-controlled identifiers or exception text.
                logger.warning("Calendar sync event skipped after connector error")
                counters[SyncOutcome.FAILED] += 1
        if connector.authoritative_snapshot:
            counters.update(
                await _reconcile_missing_provider_events(
                    context=context, seen_uids=seen_uids, cutoff=cutoff,
                )
            )
        integration.last_synced_at = datetime.now(UTC)
        failed = counters[SyncOutcome.FAILED]
        integration.last_sync_error = (
            f"{failed} calendar event(s) failed during partial sync" if failed else None
        )
        await integration_repo.save(integration)
    except Exception as exc:
        # Only connector errors carry curated, secret-free texts; anything else
        # may embed URLs or credentials (#463).
        integration.last_sync_error = (
            str(exc)[:500]
            if isinstance(exc, CalendarConnectorError)
            else "Synchronisierung fehlgeschlagen (interner Fehler)"
        )
        await integration_repo.save(integration)
        raise
    return SyncResult(
        created=counters[SyncOutcome.CREATED],
        updated=counters[SyncOutcome.UPDATED],
        cancelled=counters[SyncOutcome.CANCELLED],
        auto_matched=counters[SyncOutcome.AUTO_MATCHED],
        skipped=counters[SyncOutcome.SKIPPED],
        failed=counters[SyncOutcome.FAILED],
    )
