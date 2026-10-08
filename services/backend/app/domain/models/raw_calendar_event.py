"""app/domain/models/raw_calendar_event.py: Module."""

from __future__ import annotations

import hashlib
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
    revision_marker: str | None = None
    resource_id: str | None = None
    # Set only for occurrences of a recurring series; ``uid`` is then the
    # composed storage key (see ``occurrence_key``).
    series_uid: str | None = None
    recurrence_id: str | None = None
    # True for an event that exists in the source but lies outside the queried
    # window: it proves presence (no deletion) and may update a linked event,
    # but is never imported as new.
    outside_window: bool = False



EXTERNAL_EVENT_ID_MAX_LENGTH = 500  # external_event_id columns are String(500)


def occurrence_key(series_uid: str, recurrence_id: str) -> str:
    """Storage key of one occurrence of a recurring series: UID + RECURRENCE-ID.

    The key is only ever composed, never parsed back: callers carry
    ``series_uid``/``recurrence_id`` explicitly. Overlong UIDs are replaced by
    their SHA-256 so the key always fits the external_event_id columns.
    """
    key = f"{series_uid}::{recurrence_id}"
    if len(key) <= EXTERNAL_EVENT_ID_MAX_LENGTH:
        return key
    digest = hashlib.sha256(series_uid.encode()).hexdigest()
    return f"sha256:{digest}::{recurrence_id}"
