from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class EventSource(StrEnum):
    """Origin of an event instance."""
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class EventVisibility(StrEnum):
    """Visibility of an event instance."""
    INTERNAL = "INTERNAL"
    PUBLIC = "PUBLIC"


class SyncState(StrEnum):
    """Sync state for calendar event instances."""
    CLEAN = "CLEAN"
    DIRTY_INTERNAL = "DIRTY_INTERNAL"
    DIRTY_EXTERNAL = "DIRTY_EXTERNAL"
    CONFLICT = "CONFLICT"


@dataclass
class EventInstance:
    id: uuid.UUID
    planning_slot_id: uuid.UUID
    title: str
    actual_start_at: datetime
    actual_end_at: datetime
    source: EventSource
    visibility: EventVisibility
    deviation_flag: bool
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    sync_state: SyncState = SyncState.CLEAN
    external_uid: str | None = None
    content_hash: str | None = None
    calendar_integration_id: uuid.UUID | None = None
    last_external_modified_at: datetime | None = None
    last_internal_modified_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        planning_slot_id: uuid.UUID,
        title: str,
        actual_start_at: datetime,
        actual_end_at: datetime,
        source: EventSource,
        visibility: EventVisibility,
        description: str | None = None,
        deviation_flag: bool = False,
        instance_id: uuid.UUID | None = None,
        sync_state: SyncState = SyncState.CLEAN,
        external_uid: str | None = None,
        content_hash: str | None = None,
        calendar_integration_id: uuid.UUID | None = None,
        last_external_modified_at: datetime | None = None,
        last_internal_modified_at: datetime | None = None,
    ) -> EventInstance:
        now = datetime.now(timezone.utc)
        return cls(
            id=instance_id or uuid.uuid4(),
            planning_slot_id=planning_slot_id,
            title=title,
            description=description,
            actual_start_at=actual_start_at,
            actual_end_at=actual_end_at,
            source=source,
            visibility=visibility,
            deviation_flag=deviation_flag,
            sync_state=sync_state,
            external_uid=external_uid,
            content_hash=content_hash,
            calendar_integration_id=calendar_integration_id,
            last_external_modified_at=last_external_modified_at,
            last_internal_modified_at=last_internal_modified_at,
            created_at=now,
            updated_at=now,
        )
