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
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
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
from app.domain.errors import IntegrationNotFoundError, UnsupportedCalendarTypeError
from app.domain.models.calendar_integration import (
    SUPPORTED_CALENDAR_TYPES,
    CalendarCapability,
    CalendarIntegration,
    CalendarType,
    SyncDeleteMode,
)
from app.domain.models.event_instance import EventInstance, EventSource, SyncState
from app.domain.models.external_event_link import ExternalEventLink, ExternalEventLinkState
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.models.raw_calendar_event import RawCalendarEvent, is_occurrence_key
from app.domain.ports.calendar import (
    CalendarConnector,
    CalendarConnectorError,
    OccurrenceWriteBackError,
)
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


def _sync_window(now: datetime) -> tuple[datetime, datetime]:
    """Bounded provider window; reconciliation never reaches beyond it."""
    return (
        now - timedelta(days=settings.sync_window_past_days),
        now + relativedelta(months=settings.sync_window_future_months),
    )


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
    if slot and not slot.was_released and context.integration.delete_behavior == SyncDeleteMode.HARD_DELETE:
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
    # The provider's explicit cancellation replaces any snapshot-gap marker,
    # so a later un-cancel is not mistaken for a transient gap.
    existing_link.deletion_origin = "EXTERNAL"
    existing_link.deletion_reason = "provider-cancellation"
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


_INCOMPLETE_SNAPSHOT = "Kalender unvollständig geladen; Löschabgleich übersprungen"
SNAPSHOT_GAP_REASON = "missing-from-authoritative-snapshot"


async def _restore_after_snapshot_gap(
    context: SyncContext,
    raw: RawCalendarEvent,
    link: ExternalEventLink,
    instance: EventInstance,
    slot: PlanningSlot | None,
) -> bool:
    """Reactivate a slot cancelled only because the event was missing from a snapshot.

    Cancellations by planners or by the provider (STATUS:CANCELLED) carry no
    snapshot-gap marker and are never undone here; neither is a gap cancellation
    a planner has since edited or confirmed (instance no longer provider-owned).
    """
    if link.deletion_reason != SNAPSHOT_GAP_REASON or raw.is_cancelled:
        return False
    now = datetime.now(UTC)
    link.deletion_origin = None
    link.deletion_reason = None
    link.updated_at = now
    await context.link_repo.save(link)
    if instance.sync_state in (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT):
        return False
    if slot is None or slot.status != PlanningSlotStatus.CANCELLED:
        return False
    slot.status = PlanningSlotStatus.ACTIVE
    slot.updated_at = now
    await context.slot_repo.save(slot)
    return True


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
    restored = await _restore_after_snapshot_gap(context, raw, existing_link, instance, slot)
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
        return SyncOutcome.UPDATED if restored else SyncOutcome.SKIPPED
    if raw.is_cancelled:
        return await _handle_external_cancel(
            context=context, raw=raw, existing_link=existing_link,
            instance=instance, slot=slot, new_content_hash=new_content_hash,
        )
    return await _apply_external_update(
        context=context, raw=raw, existing_link=existing_link,
        instance=instance, slot=slot, new_content_hash=new_content_hash,
    )


def _original_start(raw: RawCalendarEvent) -> datetime | None:
    """Start of the occurrence a RECURRENCE-ID override replaces (moved overrides)."""
    rid = raw.recurrence_id
    if not rid:
        return None
    if rid.endswith("Z"):
        return datetime.strptime(rid, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    day = datetime.strptime(rid, "%Y%m%d")
    return day.replace(tzinfo=ZoneInfo(settings.sync_default_timezone)).astimezone(UTC)


async def _find_link(context: SyncContext, raw: RawCalendarEvent) -> ExternalEventLink | None:
    """Look up the link for ``raw``, adopting a pre-#465 series link if it matches.

    Before #465 a recurring series was stored once under its plain UID (the
    master). The occurrence starting exactly at the master's linked instance
    takes over that link, so its slot is updated rather than cancelled.
    """
    link = await context.link_repo.get_by_external_event(
        provider=context.integration.type.value,
        external_event_id=raw.uid,
        calendar_integration_id=context.integration_id,
    )
    if link is not None or raw.series_uid is None:
        return link
    legacy = await context.link_repo.get_by_external_event(
        provider=context.integration.type.value,
        external_event_id=raw.series_uid,
        calendar_integration_id=context.integration_id,
    )
    if (
        legacy is None
        or legacy.state != ExternalEventLinkState.ACTIVE
        or legacy.event_instance_id is None
    ):
        return None
    instance = await context.instance_repo.get(legacy.event_instance_id)
    if instance is None or instance.actual_start_at not in (raw.start_at, _original_start(raw)):
        return None
    legacy.external_event_id = raw.uid
    legacy.updated_at = datetime.now(UTC)
    await context.link_repo.save(legacy)
    return legacy


async def _gone_at_provider(
    context: SyncContext, link: ExternalEventLink, seen_resources: set[str]
) -> bool:
    """Whether a link missing from a window-bounded result was really deleted.

    A returned resource was expanded completely, so a missing occurrence of it
    is authoritative. A resource missing as a whole may have moved outside the
    window: only a confirmed 404/410 counts; no href or an error never deletes.
    """
    resource_id = link.provider_resource_id
    if resource_id in seen_resources:
        return True
    if not resource_id:
        return False
    try:
        return not await context.connector.resource_exists(context.credentials, resource_id)
    except CalendarConnectorError:
        logger.warning("Calendar presence check failed; deletion skipped")
        return False


async def _reconcile_missing_provider_events(
    *,
    context: SyncContext,
    seen_uids: set[str],
    seen_resources: set[str],
    window: tuple[datetime, datetime],
) -> Counter[SyncOutcome]:
    """Reconcile links absent from a complete authoritative provider window.

    Only events inside the queried window can be judged missing; anything
    outside it was simply not asked for and stays untouched.
    """
    window_start, window_end = window
    outcomes: Counter[SyncOutcome] = Counter()
    for link in await context.link_repo.list_active_by_integration(context.integration_id):
        if link.external_event_id in seen_uids or link.event_instance_id is None:
            continue
        instance = await context.instance_repo.get(link.event_instance_id)
        if (
            instance is None
            # Provider windows are half-open: an event ending at the start or
            # starting at the end is not part of the response (RFC 4791 9.9).
            or instance.actual_end_at <= window_start
            or instance.actual_start_at >= window_end
        ):
            continue
        if context.connector.window_bounded_snapshot and not await _gone_at_provider(
            context, link, seen_resources
        ):
            continue
        slot = await context.slot_repo.get(instance.planning_slot_id)
        if instance.sync_state in (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT):
            instance.sync_state = SyncState.CONFLICT
            await context.instance_repo.save(instance)
            outcomes[SyncOutcome.SKIPPED] += 1
            continue
        now = datetime.now(UTC)
        if slot and not slot.was_released and context.integration.delete_behavior == SyncDeleteMode.HARD_DELETE:
            link.event_instance_id = None
            link.state = ExternalEventLinkState.SYNC_TOMBSTONE
            link.deletion_origin = "EXTERNAL"
            link.deletion_reason = SNAPSHOT_GAP_REASON
            link.tombstoned_at = now
            link.updated_at = now
            await context.link_repo.save(link)
            await context.slot_repo.delete(slot.id)
            outcomes[SyncOutcome.CANCELLED] += 1
        elif slot and slot.status != PlanningSlotStatus.CANCELLED:
            slot.status = PlanningSlotStatus.CANCELLED
            slot.updated_at = now
            # Marks this cancellation as reversible: only a cancel caused by
            # absence is undone when the provider shows the event again.
            link.deletion_origin = "EXTERNAL"
            link.deletion_reason = SNAPSHOT_GAP_REASON
            link.updated_at = now
            await context.slot_repo.save(slot)
            await context.link_repo.save(link)
            outcomes[SyncOutcome.CANCELLED] += 1
    return outcomes


async def _writable_links(
    instance: EventInstance,
    link_repo: SqlExternalEventLinkRepository,
    integration_repo: SqlCalendarIntegrationRepository,
) -> list[tuple[ExternalEventLink, CalendarIntegration]]:
    """Active links of writable integrations, validated before any provider write.

    Refuses unsupported providers (no outbound writes with static Google/Microsoft
    tokens, #467) and series occurrences up front, so a mixed set of links fails
    without partial writes. Links do not persist ``recurrence_id``, so occurrences
    are recognized by their stored key.
    """
    writable: list[tuple[ExternalEventLink, CalendarIntegration]] = []
    for link in await link_repo.list_by_event_instance(instance.id):
        if link.state != ExternalEventLinkState.ACTIVE:
            continue
        integration = await integration_repo.get(link.calendar_integration_id)
        if integration is None or CalendarCapability.WRITE not in integration.capabilities:
            continue
        if integration.type not in SUPPORTED_CALENDAR_TYPES:
            raise UnsupportedCalendarTypeError(integration.type)
        if is_occurrence_key(link.external_event_id):
            raise OccurrenceWriteBackError()
        writable.append((link, integration))
    return writable


async def push_deviation_resolution(instance: EventInstance, session: AsyncSession) -> bool:
    """Push resolved times immediately to writable provider links."""
    link_repo = SqlExternalEventLinkRepository(session)
    integration_repo = SqlCalendarIntegrationRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    writable_links = await _writable_links(instance, link_repo, integration_repo)
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
    internal_payload = _instance_payload(instance)
    writable_links = await _writable_links(instance, link_repo, integration_repo)
    for link, _ in writable_links:
        changed_fields = _changed_fields(internal_payload, link.last_synced_payload)
        unsupported_fields = changed_fields - {"actual_start_at", "actual_end_at"}
        if unsupported_fields:
            fields = ", ".join(sorted(unsupported_fields))
            raise CalendarConnectorError(
                f"Konflikt enthält nicht schreibbare Felder: {fields}"
            )

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


async def _sync_one(
    context: SyncContext, raw: RawCalendarEvent, existing_link: ExternalEventLink | None
) -> SyncOutcome:
    """Process one provider event; connector errors are isolated per event."""
    new_content_hash = _compute_content_hash(raw)
    try:
        if existing_link is None:
            return await _import_new_event(
                raw=raw, context=context, new_content_hash=new_content_hash
            )
        return await _process_existing_event(
            raw=raw, context=context, existing_link=existing_link,
            new_content_hash=new_content_hash,
        )
    except CalendarConnectorError:
        # Never include provider-controlled identifiers or exception text.
        logger.warning("Calendar sync event skipped after connector error")
        return SyncOutcome.FAILED


async def run_sync(
    integration_id: uuid.UUID, session: AsyncSession, *, now: datetime | None = None
) -> SyncResult:
    """Sync one CalendarIntegration. Return successful, skipped and failed counts.

    ``now`` anchors the sync window (tests pin it; production uses the clock).
    """
    lock_key = int.from_bytes(integration_id.bytes[:8], "big", signed=True)
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    integration_repo = SqlCalendarIntegrationRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    slot_repo = SqlPlanningSlotRepository(session)
    link_repo = SqlExternalEventLinkRepository(session)
    integration = await integration_repo.get(integration_id)
    if integration is None:
        raise IntegrationNotFoundError(f"CalendarIntegration {integration_id} not found")
    if integration.type not in SUPPORTED_CALENDAR_TYPES:
        raise UnsupportedCalendarTypeError(integration.type)
    counters: Counter[SyncOutcome] = Counter()
    try:
        credentials = decrypt_credentials(integration.credentials_enc)
        connector = _get_connector(integration.type)
        context = SyncContext(
            integration_id=integration_id, session=session, integration=integration,
            connector=connector, credentials=credentials,
            instance_repo=instance_repo, slot_repo=slot_repo, link_repo=link_repo,
        )
        window = _sync_window(now or datetime.now(UTC))
        raw_events = await connector.fetch_events(
            credentials, from_dt=window[0], to_dt=window[1]
        )
        seen_uids: set[str] = set()
        outside_window: list[RawCalendarEvent] = []
        for raw in raw_events:
            if raw.uid in seen_uids:
                # Two source events map to one identity; never let them flip-flop.
                logger.warning("Calendar sync event skipped: duplicate identity in snapshot")
                counters[SyncOutcome.FAILED] += 1
                continue
            seen_uids.add(raw.uid)
            if raw.outside_window:
                outside_window.append(raw)
                continue
            counters[await _sync_one(context, raw, await _find_link(context, raw))] += 1
        if outside_window:
            # Presence beyond the window: update known events (e.g. moved by the
            # provider), never import unknown ones. One query instead of N.
            active = {
                link.external_event_id: link
                for link in await link_repo.list_active_by_integration(integration_id)
            }
            for raw in outside_window:
                if raw.uid in active:
                    counters[await _sync_one(context, raw, active[raw.uid])] += 1
        incomplete = connector.authoritative_snapshot and not connector.snapshot_complete
        if incomplete:
            logger.warning("Calendar snapshot incomplete; deletion reconciliation skipped")
        elif connector.authoritative_snapshot:
            counters.update(
                await _reconcile_missing_provider_events(
                    context=context,
                    seen_uids=seen_uids,
                    seen_resources={raw.resource_id for raw in raw_events if raw.resource_id},
                    window=window,
                )
            )
        integration.last_synced_at = datetime.now(UTC)
        failed = counters[SyncOutcome.FAILED]
        problems = [f"{failed} calendar event(s) failed during partial sync"] if failed else []
        if incomplete:
            problems.append(_INCOMPLETE_SNAPSHOT)
        integration.last_sync_error = "; ".join(problems) or None
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
