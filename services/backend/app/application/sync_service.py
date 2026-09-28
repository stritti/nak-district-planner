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

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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
from app.domain.models.calendar_integration import CalendarCapability, CalendarType
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.calendar import CalendarConnector, CalendarConnectorError
from app.domain.services.sync_policy import (
    INTERNAL_DELETE_MARKER,
    SyncDeleteMode,
    SyncFieldAuthority,
    classify_field,
    inbound_state,
)

logger = logging.getLogger(__name__)


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


def _compute_content_hash(raw_event) -> str:
    """Compute deterministic SHA-256 hash for external event change detection."""
    import hashlib

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


CREATED = "created"
UPDATED = "updated"
CANCELLED = "cancelled"
AUTO_MATCHED = "auto_matched"
SKIPPED = "skipped"


async def _import_new_event(
    *,
    raw,
    integration,
    integration_id: uuid.UUID,
    session: AsyncSession,
    instance_repo: SqlEventInstanceRepository,
    slot_repo: SqlPlanningSlotRepository,
    link_repo: SqlExternalEventLinkRepository,
    new_content_hash: str,
) -> str:
    """Handle a raw event without an existing ExternalEventLink."""
    # Skip cancelled events — don't create phantom slots for them
    if raw.is_cancelled:
        return SKIPPED

    # Auto-matching: try to match to an existing PlanningSlot first
    matched_slot = await _find_matching_planning_slot(
        session=session,
        district_id=integration.district_id,
        congregation_id=integration.congregation_id,
        event_start=raw.start_at,
        event_category=raw.title,
    )

    if matched_slot is not None:
        # Auto-match: update existing EventInstance with external data
        instance = await instance_repo.get_by_planning_slot(matched_slot.id)
        if instance is not None:
            deviation = _has_significant_deviation(matched_slot, raw.start_at)
            instance.actual_start_at = raw.start_at
            instance.actual_end_at = raw.end_at
            instance.title = raw.title
            instance.description = raw.description
            instance.source = EventSource.EXTERNAL
            instance.sync_state = SyncState.CLEAN
            instance.content_hash = new_content_hash
            instance.external_uid = raw.uid
            instance.calendar_integration_id = integration_id
            instance.last_external_modified_at = datetime.now(UTC)
            instance.deviation_flag = deviation
            instance.updated_at = datetime.now(UTC)
            await instance_repo.save(instance)

            link = ExternalEventLink.create(
                event_instance_id=instance.id,
                provider=integration.type.value,
                external_event_id=raw.uid,
                calendar_integration_id=integration_id,
                last_synced_hash=new_content_hash,
            )
            await link_repo.save(link)
            return AUTO_MATCHED

    # No match — create new PlanningSlot + EventInstance
    slot = PlanningSlot.create(
        district_id=integration.district_id,
        planning_date=raw.start_at.date(),
        planning_time=raw.start_at.time(),
        congregation_id=integration.congregation_id,
        category=integration.default_category or raw.title,
        title=raw.title,
    )
    await slot_repo.save(slot)

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
        calendar_integration_id=integration_id,
    )
    await instance_repo.save(instance)

    link = ExternalEventLink.create(
        event_instance_id=instance.id,
        provider=integration.type.value,
        external_event_id=raw.uid,
        calendar_integration_id=integration_id,
        last_synced_hash=new_content_hash,
    )
    await link_repo.save(link)
    return CREATED


async def _push_internal_delete(
    *,
    connector: CalendarConnector,
    credentials: dict,
    raw,
    integration,
    existing_link: ExternalEventLink,
    instance: EventInstance,
    instance_repo: SqlEventInstanceRepository,
    link_repo: SqlExternalEventLinkRepository,
    new_content_hash: str,
) -> None:
    """Push an internal cancellation to the provider exactly once."""
    await connector.delete_event(credentials, raw)
    existing_link.revision_marker = INTERNAL_DELETE_MARKER
    existing_link.last_synced_hash = new_content_hash
    existing_link.updated_at = datetime.now(UTC)
    await link_repo.save(existing_link)
    instance.sync_state = SyncState.CLEAN
    await instance_repo.save(instance)


async def _handle_external_cancel(
    *,
    raw,
    existing_link: ExternalEventLink,
    instance: EventInstance,
    slot: PlanningSlot | None,
    instance_repo: SqlEventInstanceRepository,
    slot_repo: SqlPlanningSlotRepository,
    link_repo: SqlExternalEventLinkRepository,
    new_content_hash: str,
) -> str:
    """Apply an external cancellation according to the configured delete mode."""
    if instance.sync_state in (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT):
        instance.sync_state = SyncState.CONFLICT
        await instance_repo.save(instance)
        return SKIPPED
    if slot and settings.sync_delete_mode == SyncDeleteMode.HARD_DELETE:
        existing_link.event_instance_id = None
        existing_link.last_synced_hash = new_content_hash
        await link_repo.save(existing_link)
        await slot_repo.delete(slot.id)
        return CANCELLED
    if slot and slot.status != PlanningSlotStatus.CANCELLED:
        slot.status = PlanningSlotStatus.CANCELLED
        slot.updated_at = datetime.now(UTC)
        await slot_repo.save(slot)
        existing_link.last_synced_hash = new_content_hash
        existing_link.updated_at = datetime.now(UTC)
        await link_repo.save(existing_link)
        return CANCELLED
    existing_link.last_synced_hash = new_content_hash
    existing_link.updated_at = datetime.now(UTC)
    await link_repo.save(existing_link)
    return SKIPPED


async def _apply_external_update(
    *,
    raw,
    existing_link: ExternalEventLink,
    instance: EventInstance,
    slot: PlanningSlot | None,
    instance_repo: SqlEventInstanceRepository,
    link_repo: SqlExternalEventLinkRepository,
    new_content_hash: str,
) -> str:
    """Route incoming fields by authority and advance the sync state machine."""
    next_state = inbound_state(instance.sync_state, changed=True)
    if next_state == SyncState.CONFLICT:
        instance.sync_state = next_state
        await instance_repo.save(instance)
        return SKIPPED  # Keep the acknowledged hash so this change can be retried.

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
    await instance_repo.save(instance)

    existing_link.last_synced_hash = new_content_hash
    existing_link.revision_marker = raw.revision_marker
    existing_link.updated_at = datetime.now(UTC)
    await link_repo.save(existing_link)
    return UPDATED


async def _process_existing_event(
    *,
    raw,
    integration,
    connector: CalendarConnector,
    credentials: dict,
    integration_id: uuid.UUID,
    instance_repo: SqlEventInstanceRepository,
    slot_repo: SqlPlanningSlotRepository,
    link_repo: SqlExternalEventLinkRepository,
    existing_link: ExternalEventLink,
    new_content_hash: str,
) -> str:
    """Handle a raw event with an existing ExternalEventLink."""
    if existing_link.event_instance_id is None or existing_link.revision_marker == INTERNAL_DELETE_MARKER:
        return SKIPPED  # Durable tombstone: never re-import a deleted mapping.
    instance = await instance_repo.get(existing_link.event_instance_id)
    if instance is None:
        return SKIPPED

    slot = await slot_repo.get(instance.planning_slot_id)
    if (slot and slot.status == PlanningSlotStatus.CANCELLED
            and instance.sync_state == SyncState.DIRTY_INTERNAL
            and CalendarCapability.WRITE in integration.capabilities):
        await _push_internal_delete(
            connector=connector,
            credentials=credentials,
            raw=raw,
            integration=integration,
            existing_link=existing_link,
            instance=instance,
            instance_repo=instance_repo,
            link_repo=link_repo,
            new_content_hash=new_content_hash,
        )
        return CANCELLED

    if raw.is_cancelled:
        return await _handle_external_cancel(
            raw=raw,
            existing_link=existing_link,
            instance=instance,
            slot=slot,
            instance_repo=instance_repo,
            slot_repo=slot_repo,
            link_repo=link_repo,
            new_content_hash=new_content_hash,
        )

    if existing_link.last_synced_hash == new_content_hash:
        return SKIPPED  # Unchanged — skip

    return await _apply_external_update(
        raw=raw,
        existing_link=existing_link,
        instance=instance,
        slot=slot,
        instance_repo=instance_repo,
        link_repo=link_repo,
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

    counters = {CREATED: 0, UPDATED: 0, CANCELLED: 0, AUTO_MATCHED: 0, SKIPPED: 0}

    try:
        credentials = decrypt_credentials(integration.credentials_enc)
        connector = _get_connector(integration.type)
        cutoff = datetime.now(UTC) - timedelta(days=62)
        raw_events = await connector.fetch_events(credentials, from_dt=cutoff)

        for raw in raw_events:
            existing_link = await link_repo.get_by_external_event(
                provider=integration.type.value,
                external_event_id=raw.uid,
                calendar_integration_id=integration_id,
            )

            # Provider hashes may omit descriptions. Hash normalized business data here.
            new_content_hash = _compute_content_hash(raw)

            # Partial failure isolation: one broken event never aborts the
            # whole integration sync (harden-calendar-sync-algorithm, decision 6).
            try:
                if existing_link is None:
                    outcome = await _import_new_event(
                        raw=raw,
                        integration=integration,
                        integration_id=integration_id,
                        session=session,
                        instance_repo=instance_repo,
                        slot_repo=slot_repo,
                        link_repo=link_repo,
                        new_content_hash=new_content_hash,
                    )
                else:
                    outcome = await _process_existing_event(
                        raw=raw,
                        integration=integration,
                        connector=connector,
                        credentials=credentials,
                        integration_id=integration_id,
                        instance_repo=instance_repo,
                        slot_repo=slot_repo,
                        link_repo=link_repo,
                        existing_link=existing_link,
                        new_content_hash=new_content_hash,
                    )
                counters[outcome] += 1
            except CalendarConnectorError:
                # Do not include connector-controlled values in log records.
                # External event identifiers and exception messages can contain
                # control characters and are therefore intentionally omitted.
                logger.warning(
                    "Calendar sync event skipped after connector error",
                    extra={
                        "calendar_integration_id": str(integration_id),
                        "sync_outcome": SKIPPED,
                    },
                )
                counters[SKIPPED] += 1

        # Update integration last_synced_at
        integration.last_synced_at = datetime.now(UTC)
        integration.last_sync_error = None
        await integration_repo.save(integration)
    except Exception as exc:
        integration.last_sync_error = str(exc)[:500]
        await integration_repo.save(integration)
        raise

    return SyncResult(
        created=counters[CREATED],
        updated=counters[UPDATED],
        cancelled=counters[CANCELLED],
        auto_matched=counters[AUTO_MATCHED],
        skipped=counters[SKIPPED],
    )
