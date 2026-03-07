"""Calendar sync service — UC-02.

Orchestrates the sync of a single CalendarIntegration:
  1. Load integration from DB
  2. Decrypt credentials
  3. Fetch raw events from the external source via the matching connector
  4. Hash-based deduplication:
       NEW     → create Event (source=EXTERNAL, status=DRAFT)
       CHANGED → update title/times/description/content_hash
       DELETED → set status=CANCELLED
  5. Update integration.last_synced_at

Returns the number of events created/updated/cancelled.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.calendar.ical_connector import ICalConnector
from app.adapters.db.repositories.calendar_integration import SqlCalendarIntegrationRepository
from app.adapters.db.repositories.event import SqlEventRepository
from app.application.crypto import decrypt_credentials
from app.domain.models.calendar_integration import CalendarType
from app.domain.models.event import Event, EventSource, EventStatus, EventVisibility
from app.domain.ports.calendar import CalendarConnector


def _get_connector(calendar_type: CalendarType) -> CalendarConnector:
    if calendar_type == CalendarType.ICS:
        return ICalConnector()
    raise NotImplementedError(f"No connector implemented for {calendar_type}")


async def run_sync(integration_id: uuid.UUID, session: AsyncSession) -> dict[str, int]:
    """Sync one integration. Returns a summary dict with created/updated/cancelled counts."""
    integration_repo = SqlCalendarIntegrationRepository(session)
    event_repo = SqlEventRepository(session)

    integration = await integration_repo.get(integration_id)
    if integration is None:
        raise ValueError(f"CalendarIntegration {integration_id} not found")

    credentials = decrypt_credentials(integration.credentials_enc)
    connector = _get_connector(integration.type)
    cutoff = datetime.now(timezone.utc) - timedelta(days=62)  # ~2 Monate
    raw_events = await connector.fetch_events(credentials, from_dt=cutoff)

    created = updated = cancelled = 0

    for raw in raw_events:
        existing = await event_repo.get_by_external_uid(raw.uid, integration.id)

        if existing is None:
            if raw.is_cancelled:
                continue  # nothing to cancel
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
            )
            await event_repo.save(event)
            created += 1

        else:
            if raw.is_cancelled and existing.status != EventStatus.CANCELLED:
                existing.status = EventStatus.CANCELLED
                existing.updated_at = datetime.now(timezone.utc)
                await event_repo.save(existing)
                cancelled += 1

            elif not raw.is_cancelled and existing.content_hash != raw.content_hash:
                existing.title = raw.title
                existing.start_at = raw.start_at
                existing.end_at = raw.end_at
                existing.description = raw.description
                existing.content_hash = raw.content_hash
                existing.updated_at = datetime.now(timezone.utc)
                await event_repo.save(existing)
                updated += 1

    integration.last_synced_at = datetime.now(timezone.utc)
    integration.updated_at = datetime.now(timezone.utc)
    await integration_repo.save(integration)

    return {"created": created, "updated": updated, "cancelled": cancelled}
