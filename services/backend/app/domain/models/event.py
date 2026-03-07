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
    ) -> Event:
        now = datetime.now(timezone.utc)
        return cls(
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
            created_at=now,
            updated_at=now,
        )
