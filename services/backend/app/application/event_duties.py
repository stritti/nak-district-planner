# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Duty write rules independent of SQLAlchemy and HTTP."""

from dataclasses import replace

from app.domain.models.event_duty import EventDutyAssignment, effective_categories, normalize_name


class DutyNotFoundError(ValueError):
    pass


class DutyConflictError(ValueError):
    pass


class EventDutiesService:
    def __init__(self, repository):
        self.repository = repository

    async def assign(
        self,
        district_id,
        slot_id,
        category_id,
        *,
        name=None,
        linked_user_sub=None,
        suggestion_id=None,
        replacing=None,
        revalidate=False,
        authorize_slot=None,
    ):
        repo = self.repository
        slot = await repo.lock_slot(slot_id, district_id)
        if not slot:
            raise DutyNotFoundError("Reference not found")
        if authorize_slot is not None:
            authorize_slot(slot)
        await repo.lock_category(category_id, district_id)
        categories, overrides = await repo.catalog(district_id, slot.congregation_id)
        category = next(
            (
                c
                for c in effective_categories(
                    categories, overrides, slot.category, slot.congregation_id
                )
                if c.id == category_id
            ),
            None,
        )
        if not category:
            raise DutyNotFoundError("Reference not found")
        existing = await repo.list_assignments([slot_id])
        if replacing and (
            replacing.planning_slot_id != slot_id
            or (not revalidate and not replacing.visible_in(district_id, slot.congregation_id))
        ):
            raise DutyNotFoundError("Reference not found")
        peers = [
            a
            for a in existing
            if a.duty_category_id == category_id and (not replacing or a.id != replacing.id)
        ]
        stored_count = await repo.count_assignments(slot_id, category_id)
        replaces_destination_row = bool(
            replacing is not None and replacing.duty_category_id == category_id
        )
        if stored_count - int(replaces_destination_row) >= category.capacity:
            raise DutyConflictError("Duty capacity exceeded")
        linked_name = None
        if linked_user_sub:
            eligible = await repo.eligible_users(district_id, slot.congregation_id)
            linked_name = next(
                (u["display_name"] for u in eligible if u["sub"] == linked_user_sub), None
            )
            if not linked_name:
                raise DutyNotFoundError("Reference not found")
        if suggestion_id:
            suggestion = await repo.get_suggestion(suggestion_id)
            if (
                not suggestion
                or suggestion.hidden
                or (suggestion.district_id, suggestion.congregation_id, suggestion.duty_category_id)
                != (district_id, slot.congregation_id, category_id)
                or linked_user_sub
            ):
                raise DutyNotFoundError("Reference not found")
            if name and suggestion.normalized_name != normalize_name(name):
                raise DutyNotFoundError("Reference not found")
            name = suggestion.display_name
        assignment = EventDutyAssignment.create(
            slot_id,
            category,
            slot.congregation_id,
            name,
            linked_user_sub,
            linked_display_name=linked_name,
        )
        if any(
            (assignment.linked_user_sub and p.linked_user_sub == assignment.linked_user_sub)
            or (assignment.normalized_name and p.normalized_name == assignment.normalized_name)
            for p in peers
        ):
            raise DutyConflictError("Duplicate duty identity")
        if name:
            remembered = await repo.remember(
                district_id,
                slot.congregation_id,
                category_id,
                name,
                activate=not replacing and not suggestion_id,
            )
            assignment = replace(assignment, suggestion_id=remembered.id)
        if replacing:
            assignment = replace(
                assignment,
                id=replacing.id,
                display_name=replacing.display_name if revalidate else assignment.display_name,
                duty_label=replacing.duty_label if revalidate else assignment.duty_label,
            )
        await repo.save_assignment(assignment)
        return assignment
