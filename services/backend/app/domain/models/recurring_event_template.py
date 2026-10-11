# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Pure recurring-event template rules for the opt-in monthly checklist.

Unlike PlanningSeries, these rules never create planning slots automatically.
A persisted decision and a separate application service are required to accept
an occurrence. Dates are local calendar dates; no UTC conversion occurs during
monthly expansion.
"""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo


class RecurrenceKind(StrEnum):
    WEEKLY = "WEEKLY"
    MONTHLY_DAY = "MONTHLY_DAY"
    MONTHLY_WEEKDAY = "MONTHLY_WEEKDAY"


class DecisionStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    SKIPPED = "SKIPPED"


class ChecklistStatus(StrEnum):
    OPEN = "OPEN"
    ACCEPTED = "ACCEPTED"
    SKIPPED = "SKIPPED"
    CONFLICT = "CONFLICT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class NonexistentLocalTimeError(ValueError):
    """A wall-clock time falls inside a daylight-saving clock jump."""


class AmbiguousLocalTimeError(ValueError):
    """A wall-clock time occurs twice and requires a fold selection."""


@dataclass(frozen=True, kw_only=True)
class RecurrenceRule:
    """Versioned, anchor-stable weekly or monthly repetition pattern.

    ISO weekdays are 1=Monday through 7=Sunday. The anchor fixes interval
    parity independently of the month selected in the UI.
    """

    kind: RecurrenceKind
    anchor_date: date
    interval: int = 1
    weekdays: tuple[int, ...] = ()
    day_of_month: int | None = None
    weekday: int | None = None
    ordinal: int | None = None
    version: int = 1

    def __post_init__(self) -> None:
        """Reject malformed recurrence rules at construction time."""
        if not isinstance(self.kind, RecurrenceKind):
            raise ValueError("Unknown recurrence kind")
        if not isinstance(self.anchor_date, date) or isinstance(self.anchor_date, datetime):
            raise ValueError("anchor_date must be a date")
        if self.version != 1 or type(self.interval) is not int or self.interval < 1:
            raise ValueError("Unsupported version or interval")
        if self.kind is RecurrenceKind.WEEKLY:
            if (
                not self.weekdays
                or any(type(day) is not int or day not in range(1, 8) for day in self.weekdays)
                or len(set(self.weekdays)) != len(self.weekdays)
                or self.day_of_month is not None
                or self.weekday is not None
                or self.ordinal is not None
            ):
                raise ValueError("Invalid weekly rule")
            object.__setattr__(self, "weekdays", tuple(sorted(self.weekdays)))
        elif self.kind is RecurrenceKind.MONTHLY_DAY:
            if (
                type(self.day_of_month) is not int
                or self.day_of_month not in range(1, 32)
                or self.weekdays
                or self.weekday is not None
                or self.ordinal is not None
            ):
                raise ValueError("Invalid monthly day rule")
        elif (
            type(self.weekday) is not int
            or self.weekday not in range(1, 8)
            or type(self.ordinal) is not int
            or self.ordinal not in (1, 2, 3, 4, 5, -1)
            or self.weekdays
            or self.day_of_month is not None
        ):
            raise ValueError("Invalid monthly weekday rule")


@dataclass(frozen=True, kw_only=True)
class RecurringEventTemplate:
    id: uuid.UUID
    district_id: uuid.UUID
    title: str
    category: str
    start_time: time
    duration_minutes: int
    recurrence: RecurrenceRule
    congregation_id: uuid.UUID | None = None
    description: str | None = None
    applicability: tuple[str, ...] = ()
    active_from: date | None = None
    active_until: date | None = None
    is_active: bool = True
    revision: int = 1
    timezone: str = "Europe/Berlin"

    def __post_init__(self) -> None:
        """Validate the template without consulting persistence or tenants."""
        if not self.title.strip() or not self.category.strip():
            raise ValueError("Title and category are required")
        if self.category.strip().casefold() == "gottesdienst":
            raise ValueError("Service generation is exclusively owned by PlanningSeries")
        if type(self.duration_minutes) is not int or self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("revision must be positive")
        if self.start_time.tzinfo is not None:
            raise ValueError("start_time must be local without tzinfo")
        if self.timezone != "Europe/Berlin":
            raise ValueError("Only Europe/Berlin is currently supported")
        if self.active_from and self.active_until and self.active_from > self.active_until:
            raise ValueError("active_from must not exceed active_until")
        if self.congregation_id is not None and self.applicability:
            raise ValueError("Congregation templates cannot have applicability")
        if len(set(self.applicability)) != len(self.applicability):
            raise ValueError("Duplicate applicability entries")
        if "all" in self.applicability and len(self.applicability) != 1:
            raise ValueError("'all' cannot be combined with congregation IDs")
        for entry in self.applicability:
            if entry != "all":
                try:
                    uuid.UUID(entry)
                except (ValueError, TypeError) as exc:
                    raise ValueError("Invalid applicability UUID") from exc


@dataclass(frozen=True, kw_only=True)
class RecurringEventDecision:
    id: uuid.UUID
    district_id: uuid.UUID
    template_id: uuid.UUID
    occurrence_local_date: date
    status: DecisionStatus
    created_by: str
    planning_slot_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        """Enforce skipped-decision consistency while allowing deleted slots."""
        if not isinstance(self.status, DecisionStatus):
            raise ValueError("Unknown decision status")
        if self.status is DecisionStatus.SKIPPED and self.planning_slot_id is not None:
            raise ValueError("Skipped occurrences must not reference a planning slot")

    @property
    def occurrence_key(self) -> tuple[uuid.UUID, date]:
        """Stable identity even when the accepted planning slot is moved."""
        return self.template_id, self.occurrence_local_date



def project_checklist_status(
    template: RecurringEventTemplate,
    occurrence_date: date,
    *,
    decision: RecurringEventDecision | None = None,
    has_conflict: bool = False,
    linked_slot_exists: bool = False,
) -> ChecklistStatus:
    """Project current state without mutating the template or planning slots.

    ACCEPTED decisions whose slot was removed require explicit resolution;
    never silently re-open or recreate a deleted accepted occurrence.
    """
    if decision is None:
        return ChecklistStatus.CONFLICT if has_conflict else ChecklistStatus.OPEN
    if (
        decision.district_id != template.district_id
        or decision.template_id != template.id
        or decision.occurrence_local_date != occurrence_date
    ):
        raise ValueError("Decision does not belong to this template occurrence")
    if decision.status is DecisionStatus.SKIPPED:
        return ChecklistStatus.SKIPPED
    if decision.planning_slot_id is not None and linked_slot_exists:
        return ChecklistStatus.ACCEPTED
    return ChecklistStatus.NEEDS_REVIEW


def expand_month(template: RecurringEventTemplate, year: int, month: int) -> list[date]:
    """Return occurrences in a calendar month without writing database rows.

    Months before the anchor and missing dates (31st, fifth weekday) yield no
    occurrence. Inclusive active bounds are applied to each occurrence.
    """
    first = date(year, month, 1)
    if not template.is_active:
        return []
    last_day = calendar.monthrange(year, month)[1]
    rule = template.recurrence
    month_difference = (year - rule.anchor_date.year) * 12 + month - rule.anchor_date.month
    if rule.kind is not RecurrenceKind.WEEKLY:
        if month_difference < 0 or month_difference % rule.interval:
            return []
        if rule.kind is RecurrenceKind.MONTHLY_DAY:
            candidates = (
                [date(year, month, rule.day_of_month)]
                if rule.day_of_month <= last_day
                else []
            )
        else:
            candidate = _nth_weekday(year, month, rule.weekday, rule.ordinal)
            candidates = [candidate] if candidate is not None else []
    else:
        anchor_monday = rule.anchor_date - timedelta(days=rule.anchor_date.weekday())
        candidates = []
        for day in range(1, last_day + 1):
            candidate = first + timedelta(days=day - 1)
            weeks = (candidate - anchor_monday).days // 7
            if (
                candidate >= rule.anchor_date
                and weeks % rule.interval == 0
                and candidate.isoweekday() in rule.weekdays
            ):
                candidates.append(candidate)

    return [
        candidate
        for candidate in candidates
        if candidate >= rule.anchor_date
        and (template.active_from is None or candidate >= template.active_from)
        and (template.active_until is None or candidate <= template.active_until)
    ]


def _nth_weekday(year: int, month: int, weekday: int, ordinal: int) -> date | None:
    first = date(year, month, 1)
    last = calendar.monthrange(year, month)[1]
    if ordinal == -1:
        end = date(year, month, last)
        return end - timedelta(days=(end.isoweekday() - weekday) % 7)
    day = 1 + (weekday - first.isoweekday()) % 7 + (ordinal - 1) * 7
    return date(year, month, day) if day <= last else None


def local_start_utc(
    occurrence_date: date,
    local_time: time,
    *,
    fold: int | None = None,
    timezone: str = "Europe/Berlin",
) -> datetime:
    """Convert a local time to UTC, explicitly rejecting DST gaps and ambiguity.

    On a fall-back fold the caller must select 0 (first) or 1 (second) before
    accepting the occurrence. Never silently shift a nonexistent clock time.
    """
    if timezone != "Europe/Berlin" or local_time.tzinfo is not None:
        raise ValueError("Expected naive Europe/Berlin wall-clock time")
    if fold not in (None, 0, 1) or isinstance(fold, bool):
        raise ValueError("fold must be 0, 1 or None")
    wall = datetime.combine(occurrence_date, local_time)
    tz = ZoneInfo(timezone)
    valid: dict[int, datetime] = {}
    for choice in (0, 1):
        local = wall.replace(tzinfo=tz, fold=choice)
        utc = local.astimezone(UTC)
        if utc.astimezone(tz).replace(tzinfo=None) == wall:
            valid[choice] = utc
    if not valid:
        raise NonexistentLocalTimeError("Local clock time does not exist")
    if len(set(valid.values())) == 2:
        if fold is None:
            raise AmbiguousLocalTimeError("Local clock time requires an explicit fold")
        return valid[fold]
    if fold == 1:
        raise ValueError("fold=1 is only valid for an ambiguous time")
    return valid[0]


def utc_interval(
    template: RecurringEventTemplate, occurrence_date: date, *, fold: int | None = None
) -> tuple[datetime, datetime]:
    """The duration is elapsed real time, including across DST transitions."""
    start = local_start_utc(
        occurrence_date, template.start_time, fold=fold, timezone=template.timezone
    )
    return start, start + timedelta(minutes=template.duration_minutes)
