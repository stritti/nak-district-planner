"""app/domain/models/raw_calendar_event.py: Module."""

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
    revision_marker: str | None = None
    resource_id: str | None = None


OCCURRENCE_KEY_SEPARATOR = "::"


def occurrence_key(series_uid: str, recurrence_id: str) -> str:
    """Stable identity of one occurrence of a recurring series: UID + RECURRENCE-ID.

    Non-recurring events keep their plain UID so existing links do not churn.
    """
    return f"{series_uid}{OCCURRENCE_KEY_SEPARATOR}{recurrence_id}"


def series_uid_of(uid: str) -> str | None:
    """Return the series UID if ``uid`` identifies a single occurrence, else None."""
    series, separator, _ = uid.rpartition(OCCURRENCE_KEY_SEPARATOR)
    return series if separator else None
