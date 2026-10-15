# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQL adapter. Slot/category locks serialize capacity and configuration edits."""

from dataclasses import fields
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.adapters.db.orm_models.event_duty import (
    DutyNameSuggestionORM,
    EventDutyAssignmentORM,
    EventDutyCategoryORM,
    EventTypeDutyConfigurationORM,
)
from app.adapters.db.orm_models.membership import MembershipORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.orm_models.user import UserORM
from app.domain.models.event_duty import (
    DutyNameSuggestion,
    EventDutyAssignment,
    EventDutyCategory,
    EventTypeDutyConfiguration,
    display_name,
    normalize_name,
)
from app.domain.ports.event_duties import EventDutiesRepository


def domain(kind, row):
    values = {f.name: getattr(row, f.name) for f in fields(kind)}
    if "event_categories" in values:
        values["event_categories"] = tuple(values["event_categories"])
    return kind(**values)


class SqlEventDutiesRepository(EventDutiesRepository):
    def __init__(self, session):
        self.session = session

    async def catalog(self, district_id, congregation_id=None):
        rows = (
            await self.session.scalars(
                select(EventDutyCategoryORM)
                .where(
                    EventDutyCategoryORM.district_id == district_id,
                    or_(
                        EventDutyCategoryORM.congregation_id.is_(None),
                        EventDutyCategoryORM.congregation_id == congregation_id,
                    ),
                )
                .order_by(EventDutyCategoryORM.code)
            )
        ).all()
        overrides = (
            (
                await self.session.scalars(
                    select(EventTypeDutyConfigurationORM).where(
                        EventTypeDutyConfigurationORM.district_id == district_id,
                        EventTypeDutyConfigurationORM.congregation_id == congregation_id,
                    )
                )
            ).all()
            if congregation_id
            else []
        )
        return [domain(EventDutyCategory, x) for x in rows], [
            domain(EventTypeDutyConfiguration, x) for x in overrides
        ]

    async def list_assignments(self, slot_ids):
        rows = (
            await self.session.scalars(
                select(EventDutyAssignmentORM)
                .where(EventDutyAssignmentORM.planning_slot_id.in_(slot_ids))
                .order_by(EventDutyAssignmentORM.id)
            )
        ).all()
        return [domain(EventDutyAssignment, x) for x in rows]

    async def count_assignments(self, slot_id, category_id):
        """Count every assignment, including quarantined rows hidden by RLS.

        The bounded database function returns only a count and authorizes the
        current planner against the slot, avoiding disclosure of prior-scope
        names after a congregation move.
        """
        return int(await self.session.scalar(func.duty_assignment_count(slot_id, category_id)) or 0)

    async def lock_slot(self, slot_id, district_id):
        return await self.session.scalar(
            select(PlanningSlotORM)
            .where(PlanningSlotORM.id == slot_id, PlanningSlotORM.district_id == district_id)
            .with_for_update()
        )

    async def lock_category(self, category_id, district_id):
        return await self.session.scalar(
            select(EventDutyCategoryORM)
            .where(
                EventDutyCategoryORM.id == category_id,
                EventDutyCategoryORM.district_id == district_id,
            )
            .with_for_update()
        )

    async def eligible_users(self, district_id, congregation_id):
        scope = (MembershipORM.scope_type == "DISTRICT") & (MembershipORM.scope_id == district_id)
        if congregation_id:
            scope = scope | (
                (MembershipORM.scope_type == "CONGREGATION")
                & (MembershipORM.scope_id == congregation_id)
            )
        rows = (
            await self.session.scalars(
                select(UserORM)
                .join(MembershipORM, MembershipORM.user_sub == UserORM.sub)
                .where(scope)
                .distinct()
                .order_by(UserORM.sub)
            )
        ).all()
        return [{"sub": u.sub, "display_name": u.name or u.username} for u in rows]

    async def save_assignment(self, assignment):
        row = await self.session.get(EventDutyAssignmentORM, assignment.id)
        values = {f.name: getattr(assignment, f.name) for f in fields(assignment)}
        if row:
            for key, value in values.items():
                setattr(row, key, value)
        else:
            self.session.add(EventDutyAssignmentORM(**values))
        slot = await self.session.get(PlanningSlotORM, assignment.planning_slot_id)
        slot.updated_at = datetime.now(UTC)
        await self.session.flush()

    async def remember(self, district_id, congregation_id, category_id, name, activate=False):
        values = {
            "district_id": district_id,
            "congregation_id": congregation_id,
            "duty_category_id": category_id,
            "display_name": display_name(name),
            "normalized_name": normalize_name(name),
            "hidden": False,
        }
        statement = (
            insert(DutyNameSuggestionORM)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[
                    "district_id",
                    "congregation_id",
                    "duty_category_id",
                    "normalized_name",
                ],
                set_={"hidden": False}
                if activate
                else {"normalized_name": values["normalized_name"]},
            )
            .returning(DutyNameSuggestionORM)
        )
        row = await self.session.scalar(statement)
        return domain(DutyNameSuggestion, row)

    async def get_suggestion(self, suggestion_id):
        row = await self.session.get(DutyNameSuggestionORM, suggestion_id)
        return domain(DutyNameSuggestion, row) if row else None

    async def delete_assignment(self, assignment_id):
        row = await self.session.get(EventDutyAssignmentORM, assignment_id)
        if row:
            slot = await self.session.get(PlanningSlotORM, row.planning_slot_id)
            slot.updated_at = datetime.now(UTC)
            await self.session.delete(row)
            await self.session.flush()
