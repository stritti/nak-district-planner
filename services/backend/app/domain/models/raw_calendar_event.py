from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RawCalendarEvent:
    """Normalised event received from an external calendar source.

    This is a value object used during sync — it is never persisted directly.
    The sync service maps it to the Event aggregate.
    """

    uid: str  # stable UID from the source (e.g. iCal UID)
    title: str
    start_at: datetime
    end_at: datetime
    description: str | None
    content_hash: str  # SHA-256 of (uid + start + end + title) for change detection
    is_cancelled: bool  # True if STATUS=CANCELLED in the source
