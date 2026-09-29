"""Calendar sync service — UC-02, hardened for M3.

Implements deterministic, idempotent sync with state machine:
  1. Load integration from DB
  2. Decrypt credentials
  3. Fetch raw events from external source
  4. For each raw event:
     a. Look up ExternalEventLink by (provider, uid, calendar_integration_id)
     b. If NEW:
        - Skip cancelled events
        - Try exact auto-match to PlanningSlot (congregation, date, time, category)
        - If matched: update EventInstance actual times, set sync_state=CLEAN, create link
        - If unmatched or slot is not safely assignable: create/update Candidate
     c. If EXISTING:
        - Compare content_hash → skip if unchanged
        - If raw.is_cancelled → CANCELLED status
        - Update EventInstance fields, set sync_state=DIRTY_EXTERNAL
        - Update ExternalEventLink hash
  5. Update integration.last_synced_at
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.google_connector import GoogleCalendarConnector
from app.adapters.calendar.ical_connector import ICalConnector
from app.adapters.calendar.microsoft_connector import MicrosoftGraphCalendarConnector
from app.adapters.db.locks import acquire_advisory_xact_lock
from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.external_event_candidate import (
    SqlExternalEventCandidateRepository,
)
from app.adapters.db.repositories.external_event_link import SqlExternalEventLinkRepository
from app.adapters.db.repositories.notification import SqlNotificationRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.application.crypto import decrypt_credentials
from app.config import settings
from app.domain.models.calendar_integration import CalendarCapability, CalendarType
from app.domain.models.event_instance import EventSource, SyncState
from app.domain.models.external_event_candidate import CandidateStatus, ExternalEventCandidate
from app.domain.models.notification import Notification, NotificationType
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.calendar import CalendarConnector
from app.domain.services.external_event_mapping import (
    ExternalEventMappingData,
    apply_external_event_to_instance,
    create_external_event_link,
    has_significant_deviation,
)
from app.domain.services.sync_policy import (
    SyncDeleteMode,
    SyncFieldAuthority,
    classify_field,
    inbound_state,
)


@dataclass
class SyncResult:
    """Result of a calendar sync operation.

    Attributes:
        created: Number of new EventInstances created.
        updated: Number of existing EventInstances updated.
        cancelled: Number of existing EventInstances cancelled.
        auto_matched: Number of events auto-matched to existing PlanningSlots.
    """

    created: int = 0
    updated: int = 0
    cancelled: int = 0
    auto_matched: int = 0


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


async def _find_exact_matching_planning_slot(
    *,
    session: AsyncSession,
    district_id: uuid.UUID,
    congregation_id: uuid.UUID | None,
    event_start: datetime,
    event_category: str | None,
) -> PlanningSlot | None:
    """Find an exact, governance-safe mapping target for an external event."""
    slot_repo = SqlPlanningSlotRepository(session)

    event_date = event_start.astimezone(UTC).date()

    slots = await slot_repo.list_for_date_range(
        district_id=district_id,
        from_date=event_date,
        to_date=event_date,
    )

    for slot in slots:
        if slot.congregation_id != congregation_id:
            continue
        if event_category is not None and slot.category not in (None, event_category):
            continue
        if slot.planning_time != event_start.astimezone(UTC).time():
            continue

        return slot

    return None


async def _map_external_event_to_slot(
    *,
    slot: PlanningSlot,
    raw,
    integration,
    content_hash: str,
    instance_repo: SqlEventInstanceRepository,
    link_repo: SqlExternalEventLinkRepository,
) -> bool:
    """Map an event when the slot is safe for this integration."""
    instance = await instance_repo.get_by_planning_slot(slot.id)
    if instance is not None and (
        instance.calendar_integration_id not in (None, integration.id)
        or instance.sync_state != SyncState.CLEAN
    ):
        return False

    data = ExternalEventMappingData(
        title=raw.title,
        description=raw.description,
        start_at=raw.start_at,
        end_at=raw.end_at,
        external_event_id=raw.uid,
        provider=integration.type.value,
        calendar_integration_id=integration.id,
        content_hash=content_hash,
        revision_marker=raw.revision_marker,
    )
    mapped_instance = apply_external_event_to_instance(
        slot=slot,
        instance=instance,
        data=data,
    )
    await instance_repo.save(mapped_instance)
    await link_repo.save(
        create_external_event_link(
            event_instance_id=mapped_instance.id,
            data=data,
        )
    )
    return True


async def run_sync(integration_id: uuid.UUID, session: AsyncSession) -> SyncResult:
    """Sync one CalendarIntegration. Returns {created, updated, cancelled, auto_matched}."""
    # Serialize duplicate deliveries per integration, including first-time mappings.
    # The transaction owning this session releases the lock on commit/rollback.
    await acquire_advisory_xact_lock(session, integration_id)
    integration_repo = SqlCalendarIntegrationRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    slot_repo = SqlPlanningSlotRepository(session)
    link_repo = SqlExternalEventLinkRepository(session)
    candidate_repo = SqlExternalEventCandidateRepository(session)
    notification_repo = SqlNotificationRepository(session)

    integration = await integration_repo.get(integration_id)
    if integration is None:
        raise ValueError(f"CalendarIntegration {integration_id} not found")

    created = updated = cancelled = auto_matched = 0

    try:
        credentials = decrypt_credentials(integration.credentials_enc)
        connector = _get_connector(integration.type)
        cutoff = datetime.now(UTC) - timedelta(days=62)
        raw_events = await connector.fetch_events(credentials, from_dt=cutoff)

        for raw in raw_events:
            # 1. Check for existing mapping via ExternalEventLink
            existing_link = await link_repo.get_by_external_event(
                provider=integration.type.value,
                external_event_id=raw.uid,
                calendar_integration_id=integration_id,
            )

            # Provider hashes may omit descriptions. Hash normalized business data here.
            new_content_hash = _compute_content_hash(raw)

            if existing_link is None:
                # ── NEW external event ──
                candidate = await candidate_repo.by_external_event(integration_id, raw.uid)

                # A cancellation closes a pending review item but never creates data.
                if raw.is_cancelled:
                    if candidate is not None and candidate.status == CandidateStatus.PENDING:
                        candidate.refresh(raw, new_content_hash, integration.default_category)
                        candidate.review(CandidateStatus.DISMISSED, None)
                        await candidate_repo.save(candidate)
                    continue

                matched_slot = await _find_exact_matching_planning_slot(
                    session=session,
                    district_id=integration.district_id,
                    congregation_id=integration.congregation_id,
                    event_start=raw.start_at,
                    event_category=integration.default_category,
                )

                if matched_slot is not None:
                    mapped = await _map_external_event_to_slot(
                        slot=matched_slot, raw=raw, integration=integration,
                        content_hash=new_content_hash, instance_repo=instance_repo, link_repo=link_repo,
                    )
                    if mapped:
                        if candidate is not None and candidate.status == CandidateStatus.PENDING:
                            candidate.review(CandidateStatus.ACCEPTED, None, matched_slot.id)
                            await candidate_repo.save(candidate)
                        auto_matched += 1
                        continue

                if candidate is None:
                    candidate = ExternalEventCandidate.create(
                        integration=integration, raw=raw, content_hash=new_content_hash,
                    )
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
                else:
                    candidate.refresh(raw, new_content_hash, integration.default_category)
                await candidate_repo.save(candidate)

            else:
                # ── EXISTING external event ──
                if existing_link.event_instance_id is None or existing_link.revision_marker == "internal:deleted":
                    continue  # Durable tombstone: never re-import a deleted mapping.
                instance = await instance_repo.get(existing_link.event_instance_id)
                if instance is None:
                    continue

                slot = await slot_repo.get(instance.planning_slot_id)
                if (slot and slot.status == PlanningSlotStatus.CANCELLED
                        and instance.sync_state == SyncState.DIRTY_INTERNAL
                        and CalendarCapability.WRITE in integration.capabilities):
                    await connector.delete_event(credentials, raw)
                    existing_link.revision_marker = "internal:deleted"
                    existing_link.last_synced_hash = new_content_hash
                    existing_link.updated_at = datetime.now(UTC)
                    await link_repo.save(existing_link)
                    instance.sync_state = SyncState.CLEAN
                    await instance_repo.save(instance)
                    cancelled += 1
                    continue

                if raw.is_cancelled:
                    if instance.sync_state in (SyncState.DIRTY_INTERNAL, SyncState.CONFLICT):
                        instance.sync_state = SyncState.CONFLICT
                        await instance_repo.save(instance)
                        continue
                    # Mark slot as CANCELLED
                    if slot and settings.sync_delete_mode == SyncDeleteMode.HARD_DELETE:
                        existing_link.event_instance_id = None
                        existing_link.last_synced_hash = new_content_hash
                        await link_repo.save(existing_link)
                        await slot_repo.delete(slot.id)
                        cancelled += 1
                        continue
                    if slot and slot.status != PlanningSlotStatus.CANCELLED:
                        slot.status = PlanningSlotStatus.CANCELLED
                        slot.updated_at = datetime.now(UTC)
                        await slot_repo.save(slot)
                        cancelled += 1

                    existing_link.last_synced_hash = new_content_hash
                    existing_link.updated_at = datetime.now(UTC)
                    await link_repo.save(existing_link)
                    continue

                if existing_link.last_synced_hash == new_content_hash:
                    continue  # Unchanged — skip

                next_state = inbound_state(instance.sync_state, changed=True)
                if next_state == SyncState.CONFLICT:
                    instance.sync_state = next_state
                    await instance_repo.save(instance)
                    continue  # Keep the acknowledged hash so this change can be retried.

                # Update EventInstance fields
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
                    instance.deviation_flag = has_significant_deviation(slot, raw.start_at)
                instance.content_hash = new_content_hash
                instance.last_external_modified_at = datetime.now(UTC)
                instance.updated_at = datetime.now(UTC)
                await instance_repo.save(instance)

                existing_link.last_synced_hash = new_content_hash
                existing_link.revision_marker = raw.revision_marker
                existing_link.updated_at = datetime.now(UTC)
                await link_repo.save(existing_link)
                updated += 1

        # Update integration last_synced_at
        integration.last_synced_at = datetime.now(UTC)
        integration.last_sync_error = None
        await integration_repo.save(integration)
    except Exception as exc:
        integration.last_sync_error = str(exc)[:500]
        await integration_repo.save(integration)
        raise

    return SyncResult(
        created=created,
        updated=updated,
        cancelled=cancelled,
        auto_matched=auto_matched,
    )
