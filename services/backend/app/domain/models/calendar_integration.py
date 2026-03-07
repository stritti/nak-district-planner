from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class CalendarType(str, Enum):
    GOOGLE = "GOOGLE"
    MICROSOFT = "MICROSOFT"
    CALDAV = "CALDAV"
    ICS = "ICS"


class CalendarCapability(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    WEBHOOK = "WEBHOOK"


@dataclass
class CalendarIntegration:
    id: uuid.UUID
    district_id: uuid.UUID
    name: str
    type: CalendarType
    credentials_enc: str  # Fernet-encrypted JSON blob
    sync_interval: int  # minutes between syncs
    capabilities: list[CalendarCapability]
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime
    congregation_id: uuid.UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        district_id: uuid.UUID,
        name: str,
        type: CalendarType,
        credentials_enc: str,
        sync_interval: int = 60,
        capabilities: list[CalendarCapability] | None = None,
        congregation_id: uuid.UUID | None = None,
    ) -> CalendarIntegration:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            district_id=district_id,
            congregation_id=congregation_id,
            name=name,
            type=type,
            credentials_enc=credentials_enc,
            sync_interval=sync_interval,
            capabilities=capabilities or [CalendarCapability.READ],
            is_active=True,
            last_synced_at=None,
            created_at=now,
            updated_at=now,
        )
