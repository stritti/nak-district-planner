"""Calendar sync service — UC-02.

Orchestrates the sync of a single CalendarIntegration:
  1. Load integration from DB
  2. Decrypt credentials
  3. Fetch raw events from the external source via the matching connector
  4. Hash-based deduplication:
       NEW     → auto-match to PlanningSlot or create Event (source=EXTERNAL, status=DRAFT)
       CHANGED → update title/times/description/content_hash
       DELETED → set status=CANCELLED
  5. Update integration.last_synced_at

Auto-matching (Task Group 2.4): when a NEW external event arrives, the service
checks for an existing PlanningSlot matching on congregation, date, and time
(±2 hours).  If found, the external event updates the EventInstance instead of
creating a separate Event — no candidate creation needed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.calendar.caldav_connector import CalDAVConnector
from app.adapters.calendar.google_connector import GoogleCalendarConnector
from app.adapters.calendar.ical_connector import ICalConnector
from app.adapters.calendar.microsoft_connector import MicrosoftGraphCalendarConnector
from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
from app.adapters.db.repositories.event import SqlEventRepository
from app.adapters.db.repositories.event_instance import SqlEventInstanceRepository
from app.adapters.db.repositories.planning_slot import SqlPlanningSlotRepository
from app.application.crypto import decrypt_credentials
from app.domain.models.calendar_integration import CalendarType
from app.domain.models.event import Event, EventSource, EventStatus, EventVisibility
from app.domain.ports.calendar import CalendarConnector


def _get_connector(calendar_type: CalendarType) -> CalendarConnector:
    if calendar_type == CalendarType.ICS:
        return ICalConnector()
    elif calendar_type == CalendarType.GOOGLE:
        return GoogleCalendarConnector()
    elif calendar_type == CalendarType.MICROSOFT:
        return MicrosoftGraphCalendarConnector()
    elif calendar_type == CalendarType.CALDAV:
        return CalDAVConnector()
    raise NotImplementedError(f"No connector implemented for {calendar_type}")


async def _find_matching_planning_slot(
    *,
    session: AsyncSession,
    district_id: uuid.UUID,
    congregation_id: uuid.UUID | None,
    event_start: datetime,
    event_category: str | None,
    tolerance_minutes: int = 120,
) -> bool:
    """Check if a PlanningSlot exists that closely matches an external event.

    Match criteria:
      - same district_id
      - same congregation_id (or both None)
      - same date (event start date)
      - time within ±tolerance_minutes of the slot's planning_time
      - same category (if both have one)

    Returns True if a matching slot was found and updated.
    """
    from app.domain.models.event_instance import EventInstance
    from app.domain.models.planning_slot import PlanningSlot

    slot_repo = SqlPlanningSlotRepository(session)
    instance_repo = SqlEventInstanceRepository(session)

    event_date = event_start.date()
    event_minutes = event_start.hour * 60 + event_start.minute

    # Find slots for this district/congregation/date
    slots = await slot_repo.list_for_date_range(
        district_id=district_id,
        from_date=event_date,
        to_date=event_date,
    )

    # Filter by congregation and category
    for slot in slots:
        if slot.congregation_id != congregation_id:
            continue
        if slot.category and event_category and slot.category != event_category:
            continue

        # Check time tolerance
        slot_minutes = slot.planning_time.hour * 60 + slot.planning_time.minute
        if abs(slot_minutes - event_minutes) > tolerance_minutes:
            continue

        # Match found — update EventInstance actual times
        instance = await instance_repo.get_by_planning_slot(slot.id)
        if instance is None:
            continue

        # Check if there is a deviation
        slot_dt = datetime.combine(slot.planning_date, slot.planning_time, tzinfo=UTC)
        deviation = abs((event_start - slot_dt).total_seconds()) > 300  # >5 min

        instance.actual_start_at = event_start
        instance.actual_end_at = event_start + (event_start - slot_dt)  # preserve external duration
        instance.deviation_flag = deviation
        instance.updated_at = datetime.now(UTC)
        await instance_repo.save(instance)
        return True

    return False


async def run_sync(integration_id: uuid.UUID, session: AsyncSession) -> dict[str, int]:
    """Sync one integration. Returns a summary dict with created/updated/cancelled/auto_matched counts."""
    integration_repo = SqlCalendarIntegrationRepository(session)
    event_repo = SqlEventRepository(session)

    integration = await integration_repo.get(integration_id)
    if integration is None:
        raise ValueError(f"CalendarIntegration {integration_id} not found")

    credentials = decrypt_credentials(integration.credentials_enc)
    connector = _get_connector(integration.type)
    cutoff = datetime.now(UTC) - timedelta(days=62)  # ~2 Monate
    raw_events = await connector.fetch_events(credentials, from_dt=cutoff)

    created = updated = cancelled = auto_matched = 0

    for raw in raw_events:
        existing = await event_repo.get_by_external_uid(raw.uid, integration.id)

        if existing is None:
            if raw.is_cancelled:
                continue  # nothing to cancel

            # Auto-matching: try to match to an existing PlanningSlot first
            matched = await _find_matching_planning_slot(
                session=session,
                district_id=integration.district_id,
                congregation_id=integration.congregation_id,
                event_start=raw.start_at,
                event_category=integration.default_category,
            )
            if matched:
                auto_matched += 1
                continue

            event = Event.create(
                title=raw.title,
                start_at=raw.start_at,
                end_at=raw.end_at,
                description=raw.description,
                district_id=integration.district_id,
                congregation_id=integration.congregation_id,
                source=EventSource.EXTERNAL,
                status=EventStatus.DRAFT,
                visibility=EventVisibility.INTERNAL,
                external_uid=raw.uid,
                calendar_integration_id=integration.id,
                content_hash=raw.content_hash,
                category=integration.default_category,
            )
            await event_repo.save(event)
            created += 1

        else:
            if raw.is_cancelled and existing.status != EventStatus.CANCELLED:
                existing.status = EventStatus.CANCELLED
                existing.updated_at = datetime.now(UTC)
                await event_repo.save(existing)
                cancelled += 1

            elif not raw.is_cancelled and existing.content_hash != raw.content_hash:
                existing.title = raw.title
                existing.start_at = raw.start_at
                existing.end_at = raw.end_at
                existing.description = raw.description
                existing.content_hash = raw.content_hash

                # Apply auto-categorization on update
                existing.apply_auto_categorization()

                existing.updated_at = datetime.now(UTC)
                await event_repo.save(existing)
                updated += 1

    integration.last_synced_at = datetime.now(UTC)
    integration.updated_at = datetime.now(UTC)
    await integration_repo.save(integration)

    return {
        "created": created,
        "updated": updated,
        "cancelled": cancelled,
        "auto_matched": auto_matched,
    }
