"""app/domain/models/raw_calendar_event.py: Module."""

from __future__ import annotations

import hashlib
import re
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


_OCCURRENCE_KEY = re.compile(r".::\d{8}(T\d{6}Z)?\Z", re.DOTALL)


def is_occurrence_key(external_event_id: str) -> bool:
    """Fail-safe check whether a stored key may identify a series occurrence.

    Only used to refuse write-back on links (which do not persist
    ``recurrence_id``), never to derive identity. A plain UID that happens to
    end like an occurrence key is treated as an occurrence: the only effect is
    that its write-back is refused.
    """
    return _OCCURRENCE_KEY.search(external_event_id) is not None
