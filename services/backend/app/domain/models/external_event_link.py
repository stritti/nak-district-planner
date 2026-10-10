# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/domain/models/external_event_link.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class ExternalEventLinkState(StrEnum):
    ACTIVE = "ACTIVE"
    SYNC_TOMBSTONE = "SYNC_TOMBSTONE"


@dataclass
class ExternalEventLink:
    """Maps an external calendar event to an internal EventInstance.

    Tracks sync provenance, revision markers, and hash-based change detection
    for idempotent bidirectional sync.
    """

    id: uuid.UUID
    event_instance_id: uuid.UUID | None
    provider: str  # e.g. "ICAL", "GOOGLE", "MICROSOFT", "CALDAV"
    external_event_id: str  # Stable UID from the external calendar
    calendar_integration_id: uuid.UUID  # scopes the link to one integration
    last_synced_hash: str | None = None
    revision_marker: str | None = None  # ETag or revision sequence from provider
    created_at: datetime | None = None
    updated_at: datetime | None = None
    state: ExternalEventLinkState = ExternalEventLinkState.ACTIVE
    deletion_origin: str | None = None
    deletion_reason: str | None = None
    tombstoned_at: datetime | None = None
    last_synced_payload: dict[str, str | None] | None = None
    provider_resource_id: str | None = None

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
        last_synced_payload: dict[str, str | None] | None = None,
        provider_resource_id: str | None = None,
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
            state=ExternalEventLinkState.ACTIVE,
            last_synced_payload=last_synced_payload,
            provider_resource_id=provider_resource_id,
        )
