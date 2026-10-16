# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Resource budget shared by paginated calendar provider adapters (#605).

``resilient_request`` bounds a single page including its retries; this budget
bounds the *whole* fetch: pages, collected entries, received bytes, wall-clock
time and repeated continuation tokens. Exceeding any limit aborts with a
sanitized ``CalendarConnectorError`` so a broken or hostile provider can neither
pin a worker nor exhaust memory, and the sync never commits a partial result.
"""

from __future__ import annotations

import time

from app.config import settings
from app.domain.ports.calendar import CalendarConnectorError


class PaginationBudget:
    def __init__(
        self, *, max_pages: int, max_items: int, max_bytes: int, max_seconds: float
    ) -> None:
        self._max_pages = max_pages
        self._max_items = max_items
        self._max_bytes = max_bytes
        self._deadline = time.monotonic() + max_seconds
        self._pages = 0
        self._items = 0
        self._bytes = 0
        self._seen_tokens: set[str] = set()

    @classmethod
    def from_settings(cls) -> PaginationBudget:
        return cls(
            max_pages=settings.sync_max_pages,
            max_items=settings.sync_max_events,
            max_bytes=settings.sync_max_response_bytes,
            max_seconds=settings.sync_max_fetch_seconds,
        )

    def charge(self, *, items: int, size_bytes: int, next_token: str | None) -> None:
        """Account for one fetched page; raise when any limit is exceeded."""
        self._pages += 1
        self._items += items
        self._bytes += size_bytes
        if self._pages > self._max_pages:
            raise CalendarConnectorError("Kalender-Abruf überschreitet das Limit für Seiten")
        if self._items > self._max_items:
            raise CalendarConnectorError("Kalender-Abruf überschreitet das Limit für Einträge")
        if self._bytes > self._max_bytes:
            raise CalendarConnectorError("Kalender-Abruf überschreitet das Limit für Datenmenge")
        if time.monotonic() > self._deadline:
            raise CalendarConnectorError("Kalender-Abruf überschreitet das Zeitbudget")
        if next_token:
            if next_token in self._seen_tokens:
                raise CalendarConnectorError("Kalender-Abruf wiederholt eine Folgeseite")
            self._seen_tokens.add(next_token)
