"""Notification domain model for the in-app notification system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class NotificationType(StrEnum):
    """Categorisation of a notification."""

    EXTERNAL_EVENT_DETECTED = "EXTERNAL_EVENT_DETECTED"
    SYNC_CONFLICT = "SYNC_CONFLICT"
    CANDIDATE_REVIEW = "CANDIDATE_REVIEW"
    ASSIGNMENT_REMINDER = "ASSIGNMENT_REMINDER"
    SYSTEM = "SYSTEM"


@dataclass
class Notification:
    """A single in-app notification scoped to a district."""

    id: uuid.UUID
    district_id: uuid.UUID
    type: NotificationType
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None = None
    congregation_id: uuid.UUID | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    @classmethod
    def create(
        cls,
        *,
        district_id: uuid.UUID,
        type: NotificationType,
        title: str,
        body: str,
        congregation_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Notification:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid.uuid4(),
            district_id=district_id,
            type=type,
            title=title,
            body=body,
            congregation_id=congregation_id,
            payload=payload or {},
            created_at=now,
            read_at=None,
        )

    def mark_read(self) -> None:
        self.read_at = datetime.now(timezone.utc)
