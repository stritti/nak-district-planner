"""app/domain/ports/calendar.py: Module."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.models.raw_calendar_event import RawCalendarEvent


class CalendarConnector(ABC):
    """Port: fetch events from an external calendar source.

    Implementations live in adapters/calendar/.  The connector receives
    *decrypted* credentials (a plain dict) so it stays framework-free.
    """

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
