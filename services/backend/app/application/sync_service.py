"""Calendar sync service — UC-02, hardened for M3.

Implements deterministic, idempotent sync with state machine:
  1. Load integration from DB
  2. Decrypt credentials
  3. Fetch raw events from external source
  4. For each raw event:
     a. Look up ExternalEventLink by (provider, uid, calendar_integration_id)
     b. If NEW:
        - Skip cancelled events
        - Try auto-match to PlanningSlot (congregation, date, time ±2h, category)
        - If matched: update EventInstance actual times, set sync_state=CLEAN, create link
        - If unmatched: create new PlanningSlot + EventInstance (source=EXTERNAL) + link
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
from datetime import UTC, date, datetime, timedelta

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
from app.domain.models.calendar_integration import CalendarType
from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility, SyncState
from app.domain.models.external_event_link import ExternalEventLink
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.ports.calendar import CalendarConnector


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


async def run_sync(integration_id: uuid.UUID, session: AsyncSession) -> SyncResult:
    """Sync one CalendarIntegration. Returns {created, updated, cancelled, auto_matched}."""
    integration_repo = SqlCalendarIntegrationRepository(session)
    instance_repo = SqlEventInstanceRepository(session)
    slot_repo = SqlPlanningSlotRepository(session)
    link_repo = SqlExternalEventLinkRepository(session)

    integration = await integration_repo.get(integration_id)
    if integration is None:
        raise ValueError(f"CalendarIntegration {integration_id} not found")

    credentials = decrypt_credentials(integration.credentials_enc)
    connector = _get_connector(integration.type)
    cutoff = datetime.now(UTC) - timedelta(days=62)
    raw_events = await connector.fetch_events(credentials, from_dt=cutoff)

    created = updated = cancelled = auto_matched = 0

    for raw in raw_events:
        # 1. Check for existing mapping via ExternalEventLink
        existing_link = await link_repo.get_by_external_event(
            provider=integration.type.value,
            external_event_id=raw.uid,
            calendar_integration_id=integration_id,
        )

        # content_hash is always set by the connector; use it directly.
        new_content_hash = raw.content_hash

        if existing_link is None:
            # ── NEW external event ──

            # Skip cancelled events — don't create phantom slots for them
            if raw.is_cancelled:
                continue

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
                    auto_matched += 1
                    continue

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
            created += 1

        else:
            # ── EXISTING external event ──
            instance = await instance_repo.get(existing_link.event_instance_id)
            if instance is None:
                continue

            if existing_link.last_synced_hash == new_content_hash:
                continue  # Unchanged — skip

            if raw.is_cancelled:
                # Mark slot as CANCELLED
                slot = await slot_repo.get(instance.planning_slot_id)
                if slot and slot.status != PlanningSlotStatus.CANCELLED:
                    slot.status = PlanningSlotStatus.CANCELLED
                    slot.updated_at = datetime.now(UTC)
                    await slot_repo.save(slot)
                    cancelled += 1

                existing_link.last_synced_hash = new_content_hash
                existing_link.updated_at = datetime.now(UTC)
                await link_repo.save(existing_link)
                continue

            # Update EventInstance fields
            instance.title = raw.title
            instance.actual_start_at = raw.start_at
            instance.actual_end_at = raw.end_at
            instance.description = raw.description
            instance.source = EventSource.EXTERNAL
            instance.sync_state = SyncState.DIRTY_EXTERNAL
            instance.content_hash = new_content_hash
            instance.last_external_modified_at = datetime.now(UTC)
            instance.updated_at = datetime.now(UTC)
            await instance_repo.save(instance)

            existing_link.last_synced_hash = new_content_hash
            existing_link.updated_at = datetime.now(UTC)
            await link_repo.save(existing_link)
            updated += 1

    # Update integration last_synced_at
    integration.last_synced_at = datetime.now(UTC)
    await integration_repo.save(integration)

    return SyncResult(
        created=created,
        updated=updated,
        cancelled=cancelled,
        auto_matched=auto_matched,
    )
