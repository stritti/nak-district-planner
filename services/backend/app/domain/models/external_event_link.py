"""app/domain/models/external_event_link.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ExternalEventLink:
    """Maps an external calendar event to an internal EventInstance.

    Tracks sync provenance, revision markers, and hash-based change detection
    for idempotent bidirectional sync.
    """

    id: uuid.UUID
    event_instance_id: uuid.UUID
    provider: str  # e.g. "ICAL", "GOOGLE", "MICROSOFT", "CALDAV"
    external_event_id: str  # Stable UID from the external calendar
    calendar_integration_id: uuid.UUID  # scopes the link to one integration
    last_synced_hash: str | None = None
    revision_marker: str | None = None  # ETag or revision sequence from provider
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        event_instance_id: uuid.UUID,
        provider: str,
        external_event_id: str,
        calendar_integration_id: uuid.UUID,
        last_synced_hash: str | None = None,
        revision_marker: str | None = None,
    ) -> ExternalEventLink:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            event_instance_id=event_instance_id,
            provider=provider,
            external_event_id=external_event_id,
            calendar_integration_id=calendar_integration_id,
            last_synced_hash=last_synced_hash,
            revision_marker=revision_marker,
            created_at=now,
            updated_at=now,
        )
