"""app/domain/ports/calendar.py: Module."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.models.raw_calendar_event import RawCalendarEvent


class CalendarConnectorError(Exception):
    """Raised when a calendar connector cannot fetch or parse events."""


class OccurrenceWriteBackError(CalendarConnectorError):
    """A single occurrence of a recurring series cannot be written back.

    The series is one provider resource; writing one occurrence would rewrite
    or delete all of them.
    """

    def __init__(self) -> None:
        super().__init__(
            "Einzeltermine wiederkehrender Serien können nicht zurückgeschrieben werden"
        )


class CalendarConnector(ABC):
    """Port: fetch events from an external calendar source.

    Implementations live in adapters/calendar/.  The connector receives
    *decrypted* credentials (a plain dict) so it stays framework-free.
    """

    # A complete result lists every event in the queried window, so missing
    # events were deleted at the source.
    authoritative_snapshot: bool = False
    # Set by ``fetch_events`` per run: False when part of the source could not
    # be loaded or parsed. Deletions are then not reconciled for that run.
    snapshot_complete: bool = True

    async def update_event_times(
        self,
        credentials: dict,
        event: RawCalendarEvent,
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> str | None:
        """Update event times and return the acknowledged provider revision."""
        raise CalendarConnectorError("Dieser Kalender unterstützt keine Aktualisierungen")

    async def delete_event(self, credentials: dict, event: RawCalendarEvent) -> None:
        """Delete a fetched resource; read-only connectors explicitly refuse writes."""
        raise CalendarConnectorError("Dieser Kalender unterstützt keine Löschoperationen")

    @abstractmethod
    async def fetch_events(
        self,
        credentials: dict,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> list[RawCalendarEvent]:
        """Return all events from the external source.

        Args:
            credentials: Decrypted credential dict specific to the connector type.
                         For ICS: {"url": "https://..."}
            from_dt: Optional start of the time window filter.
            to_dt:   Optional end of the time window filter.
        """
        ...
