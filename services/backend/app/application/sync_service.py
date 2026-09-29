"""Calendar sync service — UC-02, hardened for M3.

Implements deterministic, idempotent sync with state machine:
  1. Load integration from DB
  2. Decrypt credentials
  3. Fetch raw events from external source
  4. For each raw event (isolated — one failure never aborts the run):
     a. Look up ExternalEventLink by (provider, uid, calendar_integration_id)
     b. If NEW:
        - Skip cancelled events
        - Try auto-match to PlanningSlot (congregation, date, time ±2h, category)
        - If matched: update EventInstance actual times, set sync_state=CLEAN, create link
        - If unmatched: create new PlanningSlot + EventInstance (source=EXTERNAL) + link
     c. If EXISTING:
        - Skip durable tombstones (never re-import deleted mappings)
        - Push internal cancellation to provider (WRITE capability, once)
        - If raw.is_cancelled → MARK_CANCELLED or HARD_DELETE per settings
        - Field-level authority routing; concurrent edits → CONFLICT
        - Update EventInstance fields, set sync_state, update ExternalEventLink hash
  5. Update integration.last_synced_at
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections import Counter
from dataclasses import dataclass
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
from app.config import settings
from app.domain.models.calendar_integration import CalendarCapability, CalendarIntegration, CalendarType
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError
from app.domain.services.sync_policy import (
    INTERNAL_DELETE_MARKER,
    SyncDeleteMode,
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
    """Result of a calendar sync operation.

    Attributes:
        created: Number of new EventInstances created.
        updated: Number of existing EventInstances updated.
        cancelled: Number of existing EventInstances cancelled.
        auto_matched: Number of events auto-matched to existing PlanningSlots.
        skipped: Number of events skipped after per-event connector errors.
    """

    created: int = 0
    updated: int = 0
    cancelled: int = 0
    auto_matched: int = 0
    skipped: int = 0


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
        f"|{raw_event.title}|{raw_event.description}"
    )
    return hashlib.sha256(raw_str.encode()).hexdigest()


async def _find_matching_planning_slot(
    *,
    session: AsyncSession,
    district_id: uuid.UUID,
    congregation_id: uuid.UUID | None,
    event_start: datetime,
    event_category: str | None,
    tolerance_minutes: int = 120,
) -> PlanningSlot | None:
    """Find a PlanningSlot that closely matches an external event.

    Returns the matching PlanningSlot if found, or None.
    """
    slot_repo = SqlPlanningSlotRepository(session)

    event_date = event_start.date()
    event_minutes = event_start.hour * 60 + event_start.minute

    slots = await slot_repo.list_for_date_range(
        district_id=district_id,
        from_date=event_date,
        to_date=event_date,
    )

    for slot in slots:
        if slot.congregation_id != congregation_id:
            continue
        if slot.category and event_category and slot.category != event_category:
            continue

        slot_minutes = slot.planning_time.hour * 60 + slot.planning_time.minute
        if abs(slot_minutes - event_minutes) > tolerance_minutes:
            continue

        return slot

    return None


def _has_significant_deviation(slot: PlanningSlot, event_start: datetime) -> bool:
    """Check if external event start deviates >5 min from planned time."""
    slot_dt = datetime.combine(slot.planning_date, slot.planning_time, tzinfo=UTC)
    return abs((event_start - slot_dt).total_seconds()) > 300


class SyncOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    CANCELLED = "cancelled"
    AUTO_MATCHED = "auto_matched"
    SKIPPED = "skipped"


async def _import_new_event(
    *,
    raw: RawCalendarEvent,
    context: SyncContext,
    new_content_hash: str,
) -> SyncOutcome:
    """Handle a raw event without an existing ExternalEventLink."""
    # Skip cancelled events — don't create phantom slots for them
    if raw.is_cancelled:
        return SyncOutcome.SKIPPED

    # Auto-matching: try to match to an existing PlanningSlot first
    matched_slot = await _find_matching_planning_slot(
        session=context.session,
        district_id=context.integration.district_id,
        congregation_id=context.integration.congregation_id,
        event_start=raw.start_at,
        event_category=raw.title,
    )

    if matched_slot is not None:
        # Auto-match always reuses the matched aggregate. If no EventInstance
        # exists yet, create it for this PlanningSlot instead of duplicating
        # the PlanningSlot.
        instance = await context.instance_repo.get_by_planning_slot(matched_slot.id)
        deviation = _has_significant_deviation(matched_slot, raw.start_at)
        if instance is None:
            instance = EventInstance.create(
                planning_slot_id=matched_slot.id,
                title=raw.title,
                actual_start_at=raw.start_at,
                actual_end_at=raw.end_at,
                description=raw.description,
                source=EventSource.EXTERNAL,
                visibility=EventVisibility.PUBLIC,
                sync_state=SyncState.CLEAN,
                content_hash=new_content_hash,
                external_uid=raw.uid,
                calendar_integration_id=context.integration_id,
            )
        else:
            instance.actual_start_at = raw.start_at
            instance.actual_end_at = raw.end_at
            instance.title = raw.title
            instance.description = raw.description
            instance.source = EventSource.EXTERNAL
            instance.sync_state = SyncState.CLEAN
            instance.content_hash = new_content_hash
            instance.external_uid = raw.uid
            instance.calendar_integration_id = context.integration_id
            instance.last_external_modified_at = datetime.now(UTC)
            instance.updated_at = datetime.now(UTC)

        instance.deviation_flag = deviation
        await context.instance_repo.save(instance)

        link = ExternalEventLink.create(
            event_instance_id=instance.id,
            provider=context.integration.type.value,
            external_event_id=raw.uid,
            calendar_integration_id=context.integration_id,
            last_synced_hash=new_content_hash,
        )
        await context.link_repo.save(link)
        return SyncOutcome.AUTO_MATCHED

    # No match — create new PlanningSlot + EventInstance
    slot = PlanningSlot.create(
        district_id=context.integration.district_id,
        planning_date=raw.start_at.date(),
        planning_time=raw.start_at.time(),
        congregation_id=context.integration.congregation_id,
        category=context.integration.default_category or raw.title,
        title=raw.title,
    )
    await context.slot_repo.save(slot)

    instance = EventInstance.create(
        planning_slot_id=slot.id,
        title=raw.title,
        actual_start_at=raw.start_at,
        actual_end_at=raw.end_at,
        description=raw.description,
        source=EventSource.EXTERNAL,
        visibility=EventVisibility.PUBLIC,
        sync_state=SyncState.CLEAN,
        content_hash=new_content_hash,
        external_uid=raw.uid,
        calendar_integration_id=context.integration_id,
    )
    await context.instance_repo.save(instance)

    link = ExternalEventLink.create(
        event_instance_id=instance.id,
        provider=context.integration.type.value,
        external_event_id=raw.uid,
        calendar_integration_id=context.integration_id,
        last_synced_hash=new_content_hash,
    )
    await context.link_repo.save(link)
    return SyncOutcome.CREATED


async def _push_internal_delete(
    *,
    context: SyncContext,
    raw: RawCalendarEvent,
    existing_link: ExternalEventLink,
    instance: EventInstance,
    new_content_hash: str,
) -> None:
    """Push an internal cancellation to the provider exactly once.

    Deletes deliberately bypass the fetch retry policy: an automatic retry
    could repeat a non-idempotent write. Provider revision/If-Match semantics
    are handled by the connector instead.
    """
    await context.connector.delete_event(context.credentials, raw)
    existing_link.revision_marker = INTERNAL_DELETE_MARKER
    existing_link.last_synced_hash = new_content_hash
    existing_link.updated_at = datetime.now(UTC)
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
    if slot and settings.sync_delete_mode == SyncDeleteMode.HARD_DELETE:
        existing_link.event_instance_id = None
        existing_link.last_synced_hash = new_content_hash
        await context.link_repo.save(existing_link)
        await context.slot_repo.delete(slot.id)
        return SyncOutcome.CANCELLED
    if slot and slot.status != PlanningSlotStatus.CANCELLED:
        slot.status = PlanningSlotStatus.CANCELLED
        slot.updated_at = datetime.now(UTC)
        await context.slot_repo.save(slot)
        existing_link.last_synced_hash = new_content_hash
        existing_link.updated_at = datetime.now(UTC)
        await context.link_repo.save(existing_link)
        return SyncOutcome.CANCELLED
    existing_link.last_synced_hash = new_content_hash
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
    next_state = inbound_state(instance.sync_state, changed=True)
    if next_state == SyncState.CONFLICT:
        instance.sync_state = next_state
        await context.instance_repo.save(instance)
        return SyncOutcome.SKIPPED  # Keep the acknowledged hash so this change can be retried.

    incoming = {
        "title": raw.title,
        "actual_start_at": raw.start_at,
        "actual_end_at": raw.end_at,
        "description": raw.description,
    }
    for field, value in incoming.items():
        if classify_field(field) != SyncFieldAuthority.STRUCTURAL:
            setattr(instance, field, value)
    instance.source = EventSource.EXTERNAL
    instance.sync_state = next_state
    if slot:
        instance.deviation_flag = _has_significant_deviation(slot, raw.start_at)
    instance.content_hash = new_content_hash
    instance.last_external_modified_at = datetime.now(UTC)
    instance.updated_at = datetime.now(UTC)
    await context.instance_repo.save(instance)

    existing_link.last_synced_hash = new_content_hash
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
    if existing_link.event_instance_id is None or existing_link.revision_marker == INTERNAL_DELETE_MARKER:
        return SyncOutcome.SKIPPED  # Durable tombstone: never re-import a deleted mapping.
    instance = await context.instance_repo.get(existing_link.event_instance_id)
    if instance is None:
        return SyncOutcome.SKIPPED

    slot = await context.slot_repo.get(instance.planning_slot_id)
    if (slot and slot.status == PlanningSlotStatus.CANCELLED
            and instance.sync_state == SyncState.DIRTY_INTERNAL
            and CalendarCapability.WRITE in context.integration.capabilities):
        await _push_internal_delete(
            context=context,
            raw=raw,
            existing_link=existing_link,
            instance=instance,
            new_content_hash=new_content_hash,
        )
        return SyncOutcome.CANCELLED

    if existing_link.last_synced_hash == new_content_hash:
        return SyncOutcome.SKIPPED  # Unchanged — includes acknowledged cancellations

    if raw.is_cancelled:
        return await _handle_external_cancel(
            context=context,
            raw=raw,
            existing_link=existing_link,
            instance=instance,
            slot=slot,
            new_content_hash=new_content_hash,
        )

    return await _apply_external_update(
        context=context,
        raw=raw,
        existing_link=existing_link,
        instance=instance,
        slot=slot,
        new_content_hash=new_content_hash,
    )


async def run_sync(integration_id: uuid.UUID, session: AsyncSession) -> SyncResult:
    """Sync one CalendarIntegration. Returns {created, updated, cancelled, auto_matched, skipped}."""
    # Serialize duplicate deliveries per integration, including first-time mappings.
    # The transaction owning this session releases the lock on commit/rollback.
    lock_key = int.from_bytes(integration_id.bytes[:8], "big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    integration_repo = SqlCalendarIntegrationRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    slot_repo = SqlPlanningSlotRepository(session)
    link_repo = SqlExternalEventLinkRepository(session)

    integration = await integration_repo.get(integration_id)
    if integration is None:
        raise ValueError(f"CalendarIntegration {integration_id} not found")

    counters: Counter[SyncOutcome] = Counter()

    try:
        credentials = decrypt_credentials(integration.credentials_enc)
        connector = _get_connector(integration.type)
        context = SyncContext(
            integration_id=integration_id,
            session=session,
            integration=integration,
            connector=connector,
            credentials=credentials,
            instance_repo=instance_repo,
            slot_repo=slot_repo,
            link_repo=link_repo,
        )
        cutoff = datetime.now(UTC) - timedelta(days=62)
        raw_events = await connector.fetch_events(credentials, from_dt=cutoff)

        for raw in raw_events:
            existing_link = await link_repo.get_by_external_event(
                provider=context.integration.type.value,
                external_event_id=raw.uid,
                calendar_integration_id=context.integration_id,
            )

            # Provider hashes may omit descriptions. Hash normalized business data here.
            new_content_hash = _compute_content_hash(raw)

            # Partial failure isolation: one broken event never aborts the
            # whole integration sync (harden-calendar-sync-algorithm, decision 6).
            try:
                if existing_link is None:
                    outcome = await _import_new_event(
                        raw=raw,
                        context=context,
                        new_content_hash=new_content_hash,
                    )
                else:
                    outcome = await _process_existing_event(
                        raw=raw,
                        context=context,
                        existing_link=existing_link,
                        new_content_hash=new_content_hash,
                    )
                counters[outcome] += 1
            except CalendarConnectorError:
                # Do not include connector-controlled values in log records.
                # External event identifiers and exception messages can contain
                # control characters and are therefore intentionally omitted.
                logger.warning("Calendar sync event skipped after connector error")
                counters[SyncOutcome.SKIPPED] += 1

        # Update integration last_synced_at
        integration.last_synced_at = datetime.now(UTC)
        integration.last_sync_error = None
        await integration_repo.save(integration)
    except Exception as exc:
        integration.last_sync_error = str(exc)[:500]
        await integration_repo.save(integration)
        raise

    return SyncResult(
        created=counters[SyncOutcome.CREATED],
        updated=counters[SyncOutcome.UPDATED],
        cancelled=counters[SyncOutcome.CANCELLED],
        auto_matched=counters[SyncOutcome.AUTO_MATCHED],
        skipped=counters[SyncOutcome.SKIPPED],
    )
