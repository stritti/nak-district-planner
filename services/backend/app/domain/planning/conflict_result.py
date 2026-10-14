# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum


class Severity(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ScheduledService:
    """A planned service: slot date/time (UTC) plus the actual instance times, if any."""

    congregation_id: uuid.UUID | None
    planning_date: date
    planning_time: time
    actual_start_at: datetime | None = None
    actual_end_at: datetime | None = None

    def window(self, default_duration: timedelta) -> tuple[datetime, datetime]:
        """Actual times when an EventInstance exists, else the planned slot time.

        The fallback keeps conflict checks fail-closed for slots that have no
        EventInstance yet (planning_time is stored as naive UTC).
        """
        if self.actual_start_at is not None and self.actual_end_at is not None:
            return self.actual_start_at, self.actual_end_at
        start = datetime.combine(self.planning_date, self.planning_time, tzinfo=UTC)
        return start, start + default_duration


@dataclass(frozen=True)
class ExistingAssignment:
    leader_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    congregation_id: uuid.UUID | None


@dataclass(frozen=True)
class ConflictContext:
    leader_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    congregation_id: uuid.UUID | None
    existing_assignments: tuple[ExistingAssignment, ...] = ()
    required_role: str | None = None
    unavailability_periods: tuple[tuple[datetime, datetime], ...] = ()
    min_travel_minutes: int = 30
    leader_rank: str | None = None


@dataclass(frozen=True)
class ConflictResult:
    rule_id: str
    severity: Severity
    message: str
    details: dict[str, object] = field(default_factory=dict)
