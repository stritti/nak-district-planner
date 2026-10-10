# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/domain/models/calendar_integration.py: Module."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class SyncDeleteMode(StrEnum):
    MARK_CANCELLED = "MARK_CANCELLED"
    HARD_DELETE = "HARD_DELETE"


class CalendarType(StrEnum):
    """CalendarType domain model."""

    GOOGLE = "GOOGLE"
    MICROSOFT = "MICROSOFT"
    CALDAV = "CALDAV"
    ICS = "ICS"


# Version 1.0 scope (#467): Google/Microsoft have no OAuth flow/token refresh,
# so they are not offered. Their connectors stay for the post-1.0 backlog.
SUPPORTED_CALENDAR_TYPES = frozenset({CalendarType.ICS, CalendarType.CALDAV})


class CalendarCapability(StrEnum):
    """Capabilities supported for a calendar integration.

    ``READ`` — events can be fetched from the external source (minimal).
    ``WRITE`` — events can be created/updated on the external source.
    ``WEBHOOK`` — the external source supports push-based change notifications.
    """

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
    default_category: str | None = None
    last_sync_error: str | None = None
    delete_behavior: SyncDeleteMode = SyncDeleteMode.MARK_CANCELLED

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
        default_category: str | None = None,
        delete_behavior: SyncDeleteMode = SyncDeleteMode.MARK_CANCELLED,
    ) -> CalendarIntegration:
        now = datetime.now(UTC)
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
            last_sync_error=None,
            created_at=now,
            updated_at=now,
            default_category=default_category,
            delete_behavior=delete_behavior,
        )
