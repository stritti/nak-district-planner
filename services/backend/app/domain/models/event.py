from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class EventSource(str, Enum):
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class EventStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"  # set by sync when the external source marks event deleted


class EventVisibility(str, Enum):
    INTERNAL = "INTERNAL"
    PUBLIC = "PUBLIC"


@dataclass
class Event:
    id: uuid.UUID
    title: str
    start_at: datetime
    end_at: datetime
    district_id: uuid.UUID
    source: EventSource
    status: EventStatus
    visibility: EventVisibility
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    congregation_id: uuid.UUID | None = None
    category: str | None = None
    audiences: list[str] = field(default_factory=list)
    applicability: list[uuid.UUID] = field(default_factory=list)
    # External sync fields (populated for source=EXTERNAL events)
    external_uid: str | None = None
    calendar_integration_id: uuid.UUID | None = None
    content_hash: str | None = None
    generation_slot_key: str | None = None
    invitation_source_congregation_id: uuid.UUID | None = None
    invitation_source_event_id: uuid.UUID | None = None

    def apply_auto_categorization(self) -> None:
        if "gottesdienst" in self.title.lower():
            self.category = "Gottesdienst"

    @classmethod
    def create(
        cls,
        *,
        title: str,
        start_at: datetime,
        end_at: datetime,
        district_id: uuid.UUID,
        description: str | None = None,
        congregation_id: uuid.UUID | None = None,
        category: str | None = None,
        source: EventSource = EventSource.INTERNAL,
        status: EventStatus = EventStatus.DRAFT,
        visibility: EventVisibility = EventVisibility.INTERNAL,
        audiences: list[str] | None = None,
        applicability: list[uuid.UUID] | None = None,
        external_uid: str | None = None,
        calendar_integration_id: uuid.UUID | None = None,
        content_hash: str | None = None,
        generation_slot_key: str | None = None,
        invitation_source_congregation_id: uuid.UUID | None = None,
        invitation_source_event_id: uuid.UUID | None = None,
    ) -> Event:
        now = datetime.now(timezone.utc)

        if "gottesdienst" in title.lower():
            category = "Gottesdienst"

        event = cls(
            id=uuid.uuid4(),
            title=title,
            start_at=start_at,
            end_at=end_at,
            district_id=district_id,
            description=description,
            congregation_id=congregation_id,
            category=category,
            source=source,
            status=status,
            visibility=visibility,
            audiences=audiences or [],
            applicability=applicability or [],
            external_uid=external_uid,
            calendar_integration_id=calendar_integration_id,
            content_hash=content_hash,
            generation_slot_key=generation_slot_key,
            invitation_source_congregation_id=invitation_source_congregation_id,
            invitation_source_event_id=invitation_source_event_id,
            created_at=now,
            updated_at=now,
        )
        # Re-apply in case it was explicitly passed as something else but contains the keyword
        # (Though the current logic overrides it anyway above)
        event.apply_auto_categorization()
        return event
