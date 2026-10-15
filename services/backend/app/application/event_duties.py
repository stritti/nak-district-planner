# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Duty use cases and read projection independent of SQLAlchemy and HTTP."""

from dataclasses import dataclass, replace
from uuid import UUID

from app.domain.models.event_duty import (
    EventDutyAssignment,
    EventDutyCategory,
    effective_categories,
    normalize_name,
)


class DutyNotFoundError(ValueError):
    pass


class DutyConflictError(ValueError):
    pass


@dataclass(frozen=True)
class DutyAssignmentView:
    assignment: EventDutyAssignment
    needs_review: bool
    over_capacity: bool
    quarantined: bool


@dataclass(frozen=True)
class SlotDutyView:
    categories: list[EventDutyCategory]
    assignments: list[DutyAssignmentView]


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

    async def assign(
        self,
        district_id,
        slot_id,
        category_id,
        *,
        name=None,
        linked_user_sub=None,
        suggestion_id=None,
        expected_congregation_id=_UNSET,
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
        suggestion_id=None,
        expected_congregation_id=_UNSET,
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
            name=replacing.display_name if not replacing.linked_user_sub else None,
            linked_user_sub=replacing.linked_user_sub,
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
            linked_name = await self.repository.eligible_user_display_name(
                district_id, slot.congregation_id, linked_user_sub
            )
            if not linked_name:
                raise DutyNotFoundError("Reference not found")
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
        )
        if any(
            (assignment.linked_user_sub and peer.linked_user_sub == assignment.linked_user_sub)
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
