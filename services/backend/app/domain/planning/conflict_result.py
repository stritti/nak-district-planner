from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Severity(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCK = "BLOCK"


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


@dataclass(frozen=True)
class ConflictResult:
    rule_id: str
    severity: Severity
    message: str
    details: dict[str, object] = field(default_factory=dict)