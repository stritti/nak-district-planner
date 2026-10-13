# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Explicit monthly checklist commands; no background recurrence generation.

The calling request owns the transaction. Each acceptance uses a savepoint so
even a concurrent unique-key violation cannot poison the next bulk item.
"""

from __future__ import annotations

import calendar
import uuid
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from app.domain.models.event_instance import EventInstance, EventSource, EventVisibility
from app.domain.models.planning_slot import (
    EventApprovalStatus,
    PlanningSlot,
    PlanningSlotStatus,
)
from app.domain.models.recurring_event_template import (
    AmbiguousLocalTimeError,
    ChecklistStatus,
    DecisionStatus,
    NonexistentLocalTimeError,
    RecurringEventDecision,
    RecurringEventTemplate,
    expand_month,
    local_start_utc,
    project_checklist_status,
)
from app.domain.ports.repositories import EventInstanceRepository, PlanningSlotRepository


class RecurringEventRepositoryPort(Protocol):
    """Persistence operations required by recurring-event commands."""

    async def list_decisions(
        self, district_id: uuid.UUID, from_date: date, to_date: date,
    ) -> list[RecurringEventDecision]:
        """Return decisions within the district and date range."""

    async def get_template(
        self, template_id: uuid.UUID, *, for_update: bool = False,
    ) -> RecurringEventTemplate | None:
        """Return a template, optionally locking it for a command."""

    async def get_decision(
        self, template_id: uuid.UUID, occurrence_date: date, *,
        for_update: bool = False,
    ) -> RecurringEventDecision | None:
        """Return an occurrence decision, optionally locking it."""

    async def save_decision(self, decision: RecurringEventDecision) -> None:
        """Persist an occurrence decision."""

    async def delete_decision(self, decision_id: uuid.UUID) -> None:
        """Delete an explicitly reopened decision."""

    async def find_slot_decision(self, slot_id: uuid.UUID) -> RecurringEventDecision | None:
        """Return the decision linked to a planning slot."""


class TransactionPort(Protocol):
    """Savepoint boundary owned by the calling request."""

    def begin_nested(self) -> AbstractAsyncContextManager[None]:
        """Create an asynchronous savepoint context."""


class OccurrenceConflictError(ValueError):
    """An existing decision or active planning slot forbids the requested write."""


class StaleTemplateError(OccurrenceConflictError):
    """A preview was based on an older template revision."""


class InvalidOccurrenceError(ValueError):
    """The local occurrence is no longer produced by the current template."""


@dataclass(frozen=True)
class ChecklistItem:
    template: RecurringEventTemplate
    occurrence_local_date: date
    status: ChecklistStatus
    decision_status: DecisionStatus | None = None
    planning_slot_id: uuid.UUID | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ChecklistPage:
    items: list[ChecklistItem]
    total: int
    limit: int
    offset: int
    counts: dict[str, int]


class RecurringEventService:
    """Apply domain recurrence and slot invariants through existing repositories."""

    def __init__(
        self,
        session: TransactionPort,
        recurring: RecurringEventRepositoryPort,
        slots: PlanningSlotRepository,
        instances: EventInstanceRepository,
        integrity_error_type: type[Exception] | None = None,
    ) -> None:
        self.session = session
        self.recurring = recurring
        self.slots = slots
        self.instances = instances
        self.integrity_error_type = integrity_error_type

    async def list_month(
        self,
        district_id: uuid.UUID,
        year: int,
        month: int,
        *,
        templates: list[RecurringEventTemplate],
        query: str | None = None,
        category: str | None = None,
        status_filter: ChecklistStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ChecklistPage:
        first = date(year, month, 1)
        last = date(year, month, calendar.monthrange(year, month)[1])
        decisions = {
            (decision.template_id, decision.occurrence_local_date): decision
            for decision in await self.recurring.list_decisions(district_id, first, last)
        }
        # UTC planning times may lie on the previous calendar date.
        slots = await self.slots.list_for_date_range(
            district_id=district_id,
            from_date=first - timedelta(days=1),
            to_date=last,
        )
        visible = {entry.id: entry for entry in templates}
        occurrence_keys: set[tuple[uuid.UUID, date]] = set()
        for entry in templates:
            occurrence_keys.update((entry.id, day) for day in expand_month(entry, year, month))
        # Decisions survive rule edits, exclusions, and template deactivation.
        occurrence_keys.update(key for key in decisions if key[0] in visible)
        result: list[ChecklistItem] = []
        for template_id, day in occurrence_keys:
            entry = visible[template_id]
            if query and query.casefold() not in (
                f"{entry.title} {entry.description or ''}"
            ).casefold():
                continue
            if category and entry.category != category:
                continue
            decision = decisions.get((template_id, day))
            reason = None
            has_conflict = False
            try:
                utc_start = local_start_utc(day, entry.start_time)
            except (AmbiguousLocalTimeError, NonexistentLocalTimeError):
                reason = "Lokale Uhrzeit benötigt eine manuelle Prüfung."
                utc_start = None
            if decision is None and utc_start is not None:
                has_conflict = self._has_congregation_collision(entry, utc_start, slots)
                if has_conflict:
                    reason = "Ein aktiver Gemeindetermin belegt diese Startzeit."
            # FK ON DELETE SET NULL guarantees an existing slot while the ID is
            # non-null, even if that slot is hidden by planning-slot RLS.
            linked_slot_exists = decision is not None and decision.planning_slot_id is not None
            status = project_checklist_status(
                entry, day, decision=decision, has_conflict=has_conflict,
                linked_slot_exists=linked_slot_exists,
            )
            if reason and status is ChecklistStatus.OPEN:
                status = ChecklistStatus.NEEDS_REVIEW
            if status_filter is not None and status is not status_filter:
                continue
            result.append(
                ChecklistItem(
                    template=entry,
                    occurrence_local_date=day,
                    status=status,
                    decision_status=decision.status if decision else None,
                    planning_slot_id=decision.planning_slot_id if decision else None,
                    reason=reason,
                )
            )
        result.sort(
            key=lambda item: (
                item.occurrence_local_date, item.template.start_time,
                item.template.title.casefold(), str(item.template.id),
            )
        )
        counts = {state.value: sum(item.status is state for item in result) for state in ChecklistStatus}
        return ChecklistPage(
            items=result[offset : offset + limit], total=len(result),
            limit=limit, offset=offset, counts=counts,
        )

    @staticmethod
    def _has_congregation_collision(
        entry: RecurringEventTemplate,
        utc_start: datetime,
        slots: list[PlanningSlot],
    ) -> bool:
        if entry.congregation_id is None:
            # District-level events are not mutually exclusive.
            return False
        return any(
            slot.congregation_id == entry.congregation_id
            and slot.status == PlanningSlotStatus.ACTIVE
            and slot.planning_date == utc_start.date()
            and slot.planning_time.replace(tzinfo=None)
            == utc_start.timetz().replace(tzinfo=None)
            for slot in slots
        )

    async def _current(
        self,
        entry: RecurringEventTemplate,
        occurrence_day: date,
        expected_revision: int,
        *,
        require_occurrence: bool = True,
    ) -> RecurringEventTemplate:
        current = await self.recurring.get_template(entry.id, for_update=True)
        if current is None or current.district_id != entry.district_id:
            raise InvalidOccurrenceError("Vorlage nicht verfügbar.")
        if current.revision != expected_revision:
            raise StaleTemplateError("Vorlage wurde zwischenzeitlich geändert.")
        if require_occurrence and occurrence_day not in expand_month(
            current, occurrence_day.year, occurrence_day.month
        ):
            raise InvalidOccurrenceError("Vorkommen wird von der aktuellen Vorlage nicht erzeugt.")
        return current

    async def accept(
        self,
        entry: RecurringEventTemplate,
        occurrence_day: date,
        *,
        expected_revision: int,
        created_by: str,
        local_date_override: date | None = None,
        local_time_override: time | None = None,
        title_override: str | None = None,
        description_override: str | None = None,
        duration_minutes_override: int | None = None,
        fold: int | None = None,
    ) -> RecurringEventDecision:
        try:
            async with self.session.begin_nested():
                current = await self._current(entry, occurrence_day, expected_revision)
                decision = await self.recurring.get_decision(
                    entry.id, occurrence_day, for_update=True
                )
                if decision is not None:
                    if decision.status is DecisionStatus.SKIPPED:
                        raise OccurrenceConflictError("Ausgelassene Termine erst wieder öffnen.")
                    if decision.planning_slot_id is None:
                        raise OccurrenceConflictError("Gelöschter Termin benötigt explizite Auflösung.")
                    slot = await self.slots.get(decision.planning_slot_id)
                    if slot is None:
                        raise OccurrenceConflictError("Gelöschter Termin benötigt explizite Auflösung.")
                    return decision

                local_day = local_date_override or occurrence_day
                if local_day.year < 1900:
                    raise InvalidOccurrenceError("Unzulässiges Terminjahr.")
                local_clock = local_time_override or current.start_time
                utc_start = local_start_utc(
                    local_day, local_clock, fold=fold, timezone=current.timezone
                )
                duration = (
                    duration_minutes_override
                    if duration_minutes_override is not None else current.duration_minutes
                )
                if duration <= 0:
                    raise InvalidOccurrenceError("Dauer muss positiv sein.")
                existing = await self.slots.list_for_date_range(
                    district_id=current.district_id,
                    from_date=utc_start.date(),
                    to_date=utc_start.date(),
                )
                if self._has_congregation_collision(current, utc_start, existing):
                    raise OccurrenceConflictError("Gemeinde hat bereits einen Termin zur Startzeit.")
                title = title_override if title_override is not None else current.title
                if not title.strip():
                    raise InvalidOccurrenceError("Titel darf nicht leer sein.")
                description = (
                    description_override
                    if description_override is not None else current.description
                )
                slot = PlanningSlot.create(
                    district_id=current.district_id,
                    congregation_id=current.congregation_id,
                    title=title,
                    category=current.category,
                    planning_date=utc_start.date(),
                    planning_time=utc_start.timetz().replace(tzinfo=None),
                    status=PlanningSlotStatus.ACTIVE,
                    approval_status=EventApprovalStatus.PLANNED,
                    applicability=list(current.applicability) if current.congregation_id is None else [],
                    generation_key=f"recurring-event:{current.id}:{occurrence_day.isoformat()}",
                )
                await self.slots.save(slot)
                await self.instances.save(
                    EventInstance.create(
                        planning_slot_id=slot.id,
                        title=title,
                        description=description,
                        actual_start_at=utc_start,
                        actual_end_at=utc_start + timedelta(minutes=duration),
                        source=EventSource.INTERNAL,
                        visibility=EventVisibility.PUBLIC,
                    )
                )
                decision = RecurringEventDecision(
                    id=uuid.uuid4(),
                    district_id=current.district_id,
                    template_id=current.id,
                    occurrence_local_date=occurrence_day,
                    status=DecisionStatus.ACCEPTED,
                    planning_slot_id=slot.id,
                    created_by=created_by,
                )
                await self.recurring.save_decision(decision)
                return decision
        except Exception as exc:
            if self.integrity_error_type is None or not isinstance(exc, self.integrity_error_type):
                raise
            raise OccurrenceConflictError("Vorkommen wurde parallel bearbeitet.") from exc

    async def skip(
        self,
        entry: RecurringEventTemplate,
        occurrence_day: date,
        *,
        expected_revision: int,
        created_by: str,
    ) -> RecurringEventDecision:
        try:
            async with self.session.begin_nested():
                current = await self._current(entry, occurrence_day, expected_revision)
                existing = await self.recurring.get_decision(
                    entry.id, occurrence_day, for_update=True
                )
                if existing is not None:
                    if existing.status is DecisionStatus.SKIPPED:
                        return existing
                    raise OccurrenceConflictError("Bereits übernommene Termine nur über Planung verwalten.")
                decision = RecurringEventDecision(
                    id=uuid.uuid4(),
                    district_id=current.district_id,
                    template_id=entry.id,
                    occurrence_local_date=occurrence_day,
                    status=DecisionStatus.SKIPPED,
                    created_by=created_by,
                )
                await self.recurring.save_decision(decision)
                return decision
        except Exception as exc:
            if self.integrity_error_type is None or not isinstance(exc, self.integrity_error_type):
                raise
            raise OccurrenceConflictError("Vorkommen wurde parallel bearbeitet.") from exc

    async def reopen(
        self,
        entry: RecurringEventTemplate,
        occurrence_day: date,
        *,
        expected_revision: int,
    ) -> None:
        async with self.session.begin_nested():
            await self._current(entry, occurrence_day, expected_revision)
            existing = await self.recurring.get_decision(
                entry.id, occurrence_day, for_update=True
            )
            if existing is None or existing.status is not DecisionStatus.SKIPPED:
                raise OccurrenceConflictError("Nur ausgelassene Entscheidungen können geöffnet werden.")
            await self.recurring.delete_decision(existing.id)

    async def resolve_missing_slot(
        self,
        entry: RecurringEventTemplate,
        occurrence_day: date,
        *,
        expected_revision: int,
        action: str,
        slot_id: uuid.UUID | None = None,
    ) -> RecurringEventDecision | None:
        try:
            async with self.session.begin_nested():
                current = await self._current(
                    entry, occurrence_day, expected_revision, require_occurrence=False
                )
                decision = await self.recurring.get_decision(
                    entry.id, occurrence_day, for_update=True
                )
                if decision is None or decision.status is not DecisionStatus.ACCEPTED:
                    raise OccurrenceConflictError("Keine übernommene Entscheidung zu prüfen.")
                # The FK nulls planning_slot_id on deletion; do not treat an
                # RLS-hidden still-linked slot as deleted or allow relinking it.
                if decision.planning_slot_id is not None:
                    raise OccurrenceConflictError("Verknüpfter Termin besteht noch.")
                if action == "MARK_SKIPPED":
                    updated = replace(decision, status=DecisionStatus.SKIPPED, planning_slot_id=None)
                    await self.recurring.save_decision(updated)
                    return updated
                if action == "REOPEN":
                    if occurrence_day not in expand_month(
                        current, occurrence_day.year, occurrence_day.month
                    ):
                        raise InvalidOccurrenceError("Vorlage erzeugt diesen Termin nicht mehr.")
                    await self.recurring.delete_decision(decision.id)
                    return None
                if action != "LINK_EXISTING" or slot_id is None:
                    raise InvalidOccurrenceError("LINK_EXISTING benötigt einen Planungsslot.")
                target = await self.slots.get(slot_id)
                if (
                    target is None or target.district_id != current.district_id
                    or target.congregation_id != current.congregation_id
                    or target.category != current.category
                    or target.status != PlanningSlotStatus.ACTIVE
                ):
                    raise OccurrenceConflictError("Slot gehört nicht zum passenden Bezirk/Gemeindescope.")
                # Date-only membership does not need to disambiguate a DST
                # overlap. The existing slot's UTC time is already definitive.
                target_local_date = datetime.combine(
                    target.planning_date, target.planning_time, tzinfo=UTC,
                ).astimezone(ZoneInfo(current.timezone)).date()
                if target_local_date != occurrence_day:
                    raise OccurrenceConflictError("Slot liegt nicht am geplanten Vorkommensdatum.")
                if await self.recurring.find_slot_decision(slot_id) is not None:
                    raise OccurrenceConflictError("Slot ist bereits mit einer Entscheidung verknüpft.")
                updated = replace(decision, planning_slot_id=slot_id)
                await self.recurring.save_decision(updated)
                return updated
        except Exception as exc:
            if self.integrity_error_type is None or not isinstance(exc, self.integrity_error_type):
                raise
            raise OccurrenceConflictError("Die Zuordnung wurde parallel geändert.") from exc
