# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Duty use cases and read projection independent of SQLAlchemy and HTTP."""

from dataclasses import dataclass, replace
from datetime import timedelta
from uuid import UUID

from app.config import settings
from app.domain.models.event_duty import (
    EventDutyAssignment,
    EventDutyCategory,
    effective_categories,
    normalize_name,
)
from app.domain.planning.conflict_result import Severity
from app.domain.planning.duty_conflicts import duty_identity_conflicts


class DutyNotFoundError(ValueError):
    pass


class DutyConflictError(ValueError):
    pass


class DutyIdentityConflictError(ValueError):
    """The person already holds an overlapping duty; ``conflicts`` explains which."""

    def __init__(self, conflicts):
        super().__init__("Duty identity conflict")
        self.conflicts = conflicts


@dataclass(frozen=True)
class DutyAssignmentView:
    assignment: EventDutyAssignment
    needs_review: bool
    over_capacity: bool
    quarantined: bool


@dataclass(frozen=True)
class DutyScopeImpact:
    """Dry-run result of changing a slot's category and/or congregation."""

    newly_flagged: int
    flagged_after: int
    quarantined_after: int
    newly_quarantined: int = 0

    @property
    def needs_acknowledgement(self) -> bool:
        return self.newly_flagged > 0 or self.newly_quarantined > 0

    def is_covered_by(self, newly_flagged: int, newly_quarantined: int) -> bool:
        """True when a client acknowledged at least what is about to happen."""
        return self.newly_flagged <= newly_flagged and self.newly_quarantined <= newly_quarantined


@dataclass(frozen=True)
class SlotDutyView:
    categories: list[EventDutyCategory]
    assignments: list[DutyAssignmentView]


# Sentinel that distinguishes "caller did not pass expected_congregation_id"
# from an explicit None, so slot-scope moves can be detected reliably.
_UNSET = object()


class EventDutiesService:
    def __init__(self, repository):
        self.repository = repository

    async def list_slot_duties(
        self,
        district_id,
        slot,
        *,
        include_quarantined=False,
        district_wide_planner=False,
        planner_congregation_ids: frozenset[UUID] = frozenset(),
    ) -> SlotDutyView:
        categories, overrides = await self.repository.catalog(district_id, slot.congregation_id)
        effective = effective_categories(categories, overrides, slot.category, slot.congregation_id)
        categories_by_id = {category.id: category for category in effective}
        stored_counts: dict[UUID, int] = {}
        assignments = []
        for assignment in await self.repository.list_assignments([slot.id]):
            visible = assignment.visible_in(district_id, slot.congregation_id)
            can_view_quarantine = district_wide_planner or (
                assignment.congregation_id in planner_congregation_ids
                and slot.congregation_id in planner_congregation_ids
            )
            if not visible and (not include_quarantined or not can_view_quarantine):
                continue
            category = categories_by_id.get(assignment.duty_category_id)
            if assignment.duty_category_id not in stored_counts:
                stored_counts[
                    assignment.duty_category_id
                ] = await self.repository.count_assignments(slot.id, assignment.duty_category_id)
            assignments.append(
                DutyAssignmentView(
                    assignment=assignment,
                    needs_review=not visible or category is None,
                    over_capacity=bool(
                        category and stored_counts[assignment.duty_category_id] > category.capacity
                    ),
                    quarantined=not visible,
                )
            )
        return SlotDutyView(categories=effective, assignments=assignments)

    async def preview_scope_change(
        self,
        district_id,
        slot,
        *,
        category,
        congregation_id,
    ) -> DutyScopeImpact:
        """Count duties that would need review after a category/congregation change.

        Nothing is persisted: assignments always stay stored and are only flagged
        on read (see ``list_slot_duties``), so this mirrors that projection for
        the proposed scope and subtracts what is already flagged today.
        """
        assignments = await self.repository.list_assignments([slot.id])

        async def flagged(event_category, scope_id):
            categories, overrides = await self.repository.catalog(district_id, scope_id)
            effective_ids = {
                c.id for c in effective_categories(categories, overrides, event_category, scope_id)
            }
            result = {}
            for assignment in assignments:
                visible = assignment.visible_in(district_id, scope_id)
                result[assignment.id] = (
                    not visible or assignment.duty_category_id not in effective_ids,
                    not visible,
                )
            return result

        before = await flagged(slot.category, slot.congregation_id)
        after = await flagged(category, congregation_id)
        return DutyScopeImpact(
            newly_flagged=sum(1 for key, (flag, _) in after.items() if flag and not before[key][0]),
            flagged_after=sum(1 for flag, _ in after.values() if flag),
            quarantined_after=sum(1 for _, quarantined in after.values() if quarantined),
            newly_quarantined=sum(
                1 for key, (_, quarantined) in after.items() if quarantined and not before[key][1]
            ),
        )

    async def assign(
        self,
        district_id,
        slot_id,
        category_id,
        *,
        name=None,
        linked_user_sub=None,
        leader_id=None,
        suggestion_id=None,
        expected_congregation_id=_UNSET,
        confirm_warnings=False,
    ):
        slot, category, existing, _ = await self._write_context(
            district_id,
            slot_id,
            category_id,
            expected_congregation_id=expected_congregation_id,
        )
        assignment, resolved_name = await self._build_assignment(
            district_id,
            slot,
            category,
            existing,
            name=name,
            linked_user_sub=linked_user_sub,
            leader_id=leader_id,
            suggestion_id=suggestion_id,
        )
        assignment = await self._remember_name(
            assignment,
            district_id,
            slot.congregation_id,
            category_id,
            resolved_name,
            activate=True,
        )
        await self._guard_identity_conflicts(district_id, slot, assignment, confirm_warnings)
        await self.repository.save_assignment(assignment)
        return assignment

    async def replace(
        self,
        district_id,
        slot_id,
        category_id,
        replacing,
        *,
        name=None,
        linked_user_sub=None,
        leader_id=None,
        suggestion_id=None,
        expected_congregation_id=_UNSET,
        confirm_warnings=False,
    ):
        slot, category, existing, replacing = await self._write_context(
            district_id,
            slot_id,
            category_id,
            replacing=replacing,
            expected_congregation_id=expected_congregation_id,
        )
        if not replacing.visible_in(district_id, slot.congregation_id):
            raise DutyNotFoundError("Reference not found")
        assignment, resolved_name = await self._build_assignment(
            district_id,
            slot,
            category,
            existing,
            name=name,
            linked_user_sub=linked_user_sub,
            leader_id=leader_id,
            suggestion_id=suggestion_id,
            replacing=replacing,
        )
        assignment = replace(assignment, id=replacing.id)
        assignment = await self._remember_name(
            assignment,
            district_id,
            slot.congregation_id,
            category_id,
            resolved_name,
            activate=False,
        )
        await self._guard_identity_conflicts(district_id, slot, assignment, confirm_warnings)
        await self.repository.save_assignment(assignment)
        return assignment

    async def revalidate(
        self,
        district_id,
        slot_id,
        replacing,
        *,
        expected_congregation_id=_UNSET,
    ):
        slot, category, existing, replacing = await self._write_context(
            district_id,
            slot_id,
            None,
            replacing=replacing,
            expected_congregation_id=expected_congregation_id,
        )
        assignment, resolved_name = await self._build_assignment(
            district_id,
            slot,
            category,
            existing,
            name=(
                replacing.display_name
                if not replacing.linked_user_sub and not replacing.leader_id
                else None
            ),
            linked_user_sub=replacing.linked_user_sub,
            leader_id=replacing.leader_id,
            suggestion_id=None,
            replacing=replacing,
        )
        assignment = replace(
            assignment,
            id=replacing.id,
            display_name=replacing.display_name,
            duty_label=replacing.duty_label,
        )
        assignment = await self._remember_name(
            assignment,
            district_id,
            slot.congregation_id,
            category.id,
            resolved_name,
            activate=False,
        )
        await self.repository.save_assignment(assignment)
        return assignment

    async def _guard_identity_conflicts(self, district_id, slot, assignment, confirm_warnings):
        """Refuse a duty when the same person holds an overlapping one (block or confirm)."""
        if not settings.conflict_check_enabled:
            return
        schedule = await self.repository.slot_schedule(slot.id)
        if schedule is None:
            return
        default_duration = timedelta(minutes=settings.sync_expected_duration_minutes)
        start, end = schedule.window(default_duration)
        linked_user_sub = assignment.linked_user_sub
        name_key = assignment.normalized_name or normalize_name(assignment.display_name)
        if assignment.leader_id:
            # A leader's own account and plain name are matched as well as the leader record.
            leader = await self.repository.get_leader(district_id, assignment.leader_id)
            if leader is not None:
                linked_user_sub = leader.user_sub
                name_key = normalize_name(leader.name)
        window = {
            "window_start": start - default_duration,
            "window_end": end,
            "exclude_slot_id": slot.id,
        }
        others = await self.repository.list_identity_schedule(
            district_id,
            linked_user_sub=linked_user_sub,
            normalized_name=name_key,
            leader_id=assignment.leader_id,
            **window,
        )
        if linked_user_sub and not assignment.leader_id:
            # An account duty also meets the services and duties of leaders linked to it.
            for leader_id in await self.repository.leader_ids_for_account(
                district_id, linked_user_sub
            ):
                others += await self.repository.list_identity_schedule(
                    district_id,
                    linked_user_sub=None,
                    normalized_name=None,
                    leader_id=leader_id,
                    **window,
                )
        conflicts = duty_identity_conflicts(start, end, others)
        blocking = any(conflict.severity == Severity.BLOCK for conflict in conflicts)
        unconfirmed = not confirm_warnings and any(
            conflict.severity == Severity.WARN for conflict in conflicts
        )
        if blocking or unconfirmed:
            raise DutyIdentityConflictError(conflicts)

    async def _write_context(
        self,
        district_id,
        slot_id,
        category_id,
        *,
        replacing=None,
        expected_congregation_id=_UNSET,
    ):
        slot = await self.repository.lock_slot(slot_id, district_id)
        if not slot or (
            expected_congregation_id is not _UNSET
            and slot.congregation_id != expected_congregation_id
        ):
            raise DutyNotFoundError("Reference not found")
        if replacing and replacing.planning_slot_id != slot_id:
            raise DutyNotFoundError("Reference not found")
        locked_replacing = None
        if replacing:
            locked_replacing = await self.repository.lock_assignment(replacing.id)
            if (
                not locked_replacing
                or locked_replacing.district_id != district_id
                or locked_replacing.planning_slot_id != slot_id
            ):
                raise DutyNotFoundError("Reference not found")
            if locked_replacing != replacing:
                raise DutyConflictError("Duty assignment changed concurrently")
            if category_id is None:
                category_id = locked_replacing.duty_category_id
        if category_id is None:
            raise DutyNotFoundError("Reference not found")
        if not await self.repository.lock_category(category_id, district_id):
            raise DutyNotFoundError("Reference not found")
        categories, overrides = await self.repository.catalog(district_id, slot.congregation_id)
        category = next(
            (
                candidate
                for candidate in effective_categories(
                    categories, overrides, slot.category, slot.congregation_id
                )
                if candidate.id == category_id
            ),
            None,
        )
        if category is None:
            raise DutyNotFoundError("Reference not found")
        return (
            slot,
            category,
            await self.repository.list_assignments([slot_id]),
            locked_replacing,
        )

    async def _build_assignment(
        self,
        district_id,
        slot,
        category,
        existing,
        *,
        name,
        linked_user_sub,
        suggestion_id,
        leader_id=None,
        replacing=None,
    ):
        peers = [
            assignment
            for assignment in existing
            if assignment.duty_category_id == category.id
            and (replacing is None or assignment.id != replacing.id)
        ]
        stored_count = await self.repository.count_assignments(slot.id, category.id)
        replaces_destination_row = bool(
            replacing is not None and replacing.duty_category_id == category.id
        )
        if stored_count - int(replaces_destination_row) >= category.capacity:
            raise DutyConflictError("Duty capacity exceeded")
        linked_name = None
        if linked_user_sub:
            # Same account lock a service of the leader linked to this account takes.
            await self.repository.lock_account(linked_user_sub)
            linked_name = await self.repository.eligible_user_display_name(
                district_id, slot.congregation_id, linked_user_sub
            )
            if not linked_name:
                raise DutyNotFoundError("Reference not found")
        leader_label = None
        if leader_id:
            # Held until commit; taken after the slot lock, the order service assignments use.
            await self.repository.lock_leader(leader_id)
            leader = await self.repository.get_leader(district_id, leader_id)
            # Same eligibility as a service assignment: active, not retired before the event.
            if leader is None or not leader.is_eligible_on(slot.planning_date):
                raise DutyNotFoundError("Reference not found")
            if leader.user_sub:
                await self.repository.lock_account(leader.user_sub)
            leader_label = f"{leader.rank.value} {leader.name}" if leader.rank else leader.name
        if suggestion_id:
            suggestion = await self.repository.get_suggestion(suggestion_id)
            if (
                not suggestion
                or suggestion.hidden
                or (
                    suggestion.district_id,
                    suggestion.congregation_id,
                    suggestion.duty_category_id,
                )
                != (district_id, slot.congregation_id, category.id)
                or linked_user_sub
                or leader_id
            ):
                raise DutyNotFoundError("Reference not found")
            if name and suggestion.normalized_name != normalize_name(name):
                raise DutyNotFoundError("Reference not found")
            name = suggestion.display_name
        assignment = EventDutyAssignment.create(
            slot.id,
            category,
            slot.congregation_id,
            name,
            linked_user_sub,
            linked_display_name=linked_name,
            leader_id=leader_id,
            leader_display_name=leader_label,
        )
        if any(
            (assignment.linked_user_sub and peer.linked_user_sub == assignment.linked_user_sub)
            or (assignment.leader_id and peer.leader_id == assignment.leader_id)
            or (assignment.normalized_name and peer.normalized_name == assignment.normalized_name)
            for peer in peers
        ):
            raise DutyConflictError("Duplicate duty identity")
        return assignment, name

    async def _remember_name(
        self,
        assignment,
        district_id,
        congregation_id,
        category_id,
        name,
        *,
        activate,
    ):
        if not name:
            return assignment
        remembered = await self.repository.remember(
            district_id,
            congregation_id,
            category_id,
            name,
            activate=activate,
        )
        return replace(assignment, suggestion_id=remembered.id)
