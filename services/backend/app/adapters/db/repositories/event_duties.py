# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQL adapter. Slot/category locks serialize capacity and configuration edits."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert

from app.adapters.db.orm_models.event_duty import (
    DutyNameSuggestionORM,
    EventDutyAssignmentORM,
    EventDutyCategoryORM,
    EventTypeDutyConfigurationORM,
)
from app.adapters.db.orm_models.event_instance import EventInstanceORM
from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.config import settings
from app.domain.models.event_duty import (
    DutyNameSuggestion,
    EventDutyAssignment,
    EventDutyCategory,
    EventTypeDutyConfiguration,
    display_name,
    normalize_name,
)
from app.domain.models.planning_slot import PlanningSlot, PlanningSlotStatus
from app.domain.planning.conflict_result import ScheduledService
from app.domain.planning.duty_conflicts import ScheduledDuty
from app.domain.ports.event_duties import EventDutiesRepository


def _to_domain(kind, row):
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
        return [_to_domain(EventDutyCategory, x) for x in rows], [
            _to_domain(EventTypeDutyConfiguration, x) for x in overrides
        ]

    async def list_assignments(self, slot_ids):
        rows = (
            await self.session.scalars(
                select(EventDutyAssignmentORM)
                .where(EventDutyAssignmentORM.planning_slot_id.in_(slot_ids))
                .order_by(EventDutyAssignmentORM.id)
            )
        ).all()
        return [_to_domain(EventDutyAssignment, x) for x in rows]

    async def count_assignments(self, slot_id, category_id):
        """Count every assignment, including quarantined rows hidden by RLS.

        The bounded database function returns only a count and authorizes the
        current planner against the slot, avoiding disclosure of prior-scope
        names after a congregation move.
        """
        return int(await self.session.scalar(func.duty_assignment_count(slot_id, category_id)) or 0)

    async def get_slot(self, slot_id, district_id):
        row = await self.session.scalar(
            select(PlanningSlotORM).where(
                PlanningSlotORM.id == slot_id, PlanningSlotORM.district_id == district_id
            )
        )
        return _to_domain(PlanningSlot, row) if row else None

    async def lock_slot(self, slot_id, district_id):
        row = await self.session.scalar(
            select(PlanningSlotORM)
            .where(PlanningSlotORM.id == slot_id, PlanningSlotORM.district_id == district_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return _to_domain(PlanningSlot, row) if row else None

    async def slot_schedule(self, slot_id):
        row = (
            await self.session.execute(
                select(
                    PlanningSlotORM.congregation_id,
                    PlanningSlotORM.planning_date,
                    PlanningSlotORM.planning_time,
                    EventInstanceORM.actual_start_at,
                    EventInstanceORM.actual_end_at,
                )
                .select_from(PlanningSlotORM)
                .outerjoin(EventInstanceORM, EventInstanceORM.planning_slot_id == PlanningSlotORM.id)
                .where(PlanningSlotORM.id == slot_id)
            )
        ).first()
        return ScheduledService(*row) if row else None

    async def list_identity_schedule(
        self, district_id, *, linked_user_sub, normalized_name, window_start, window_end,
        exclude_slot_id,
    ):
        identity = []
        if linked_user_sub:
            identity.append(EventDutyAssignmentORM.linked_user_sub == linked_user_sub)
        if normalized_name:
            identity.append(
                and_(
                    EventDutyAssignmentORM.linked_user_sub.is_(None),
                    EventDutyAssignmentORM.normalized_name == normalized_name,
                )
            )
        if not identity:
            return []
        rows = (
            await self.session.execute(
                select(
                    EventDutyAssignmentORM.planning_slot_id,
                    EventDutyAssignmentORM.linked_user_sub,
                    PlanningSlotORM.congregation_id,
                    PlanningSlotORM.planning_date,
                    PlanningSlotORM.planning_time,
                    EventInstanceORM.actual_start_at,
                    EventInstanceORM.actual_end_at,
                )
                .select_from(EventDutyAssignmentORM)
                .join(PlanningSlotORM, PlanningSlotORM.id == EventDutyAssignmentORM.planning_slot_id)
                .outerjoin(EventInstanceORM, EventInstanceORM.planning_slot_id == PlanningSlotORM.id)
                .where(
                    EventDutyAssignmentORM.district_id == district_id,
                    EventDutyAssignmentORM.planning_slot_id != exclude_slot_id,
                    PlanningSlotORM.status == PlanningSlotStatus.ACTIVE,
                    or_(*identity),
                    PlanningSlotORM.planning_date.between(
                        window_start.astimezone(UTC).date(), window_end.astimezone(UTC).date()
                    ),
                )
            )
        ).all()
        default_duration = timedelta(minutes=settings.sync_expected_duration_minutes)
        duties = []
        for slot_id, sub, congregation_id, day, time_, actual_start, actual_end in rows:
            start, end = ScheduledService(
                congregation_id, day, time_, actual_start, actual_end
            ).window(default_duration)
            duties.append(
                ScheduledDuty(slot_id, congregation_id, start, end, strong=sub is not None)
            )
        return duties

    async def lock_category(self, category_id, district_id):
        row = await self.session.scalar(
            select(EventDutyCategoryORM)
            .where(
                EventDutyCategoryORM.id == category_id,
                EventDutyCategoryORM.district_id == district_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return _to_domain(EventDutyCategory, row) if row else None

    async def save_category(self, category):
        row = await self.session.get(EventDutyCategoryORM, category.id)
        values = {field.name: getattr(category, field.name) for field in fields(category)}
        values["event_categories"] = list(category.event_categories)
        if row is None:
            row = EventDutyCategoryORM(**values)
            self.session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        await self.session.flush()
        return _to_domain(EventDutyCategory, row)

    async def save_configuration(self, configuration):
        row = await self.session.scalar(
            select(EventTypeDutyConfigurationORM).where(
                EventTypeDutyConfigurationORM.duty_category_id == configuration.duty_category_id,
                EventTypeDutyConfigurationORM.congregation_id == configuration.congregation_id,
            )
        )
        values = {field.name: getattr(configuration, field.name) for field in fields(configuration)}
        values["event_categories"] = list(configuration.event_categories)
        if row is None:
            row = EventTypeDutyConfigurationORM(**values)
            self.session.add(row)
        else:
            values.pop("id")
            for key, value in values.items():
                setattr(row, key, value)
        await self.session.flush()
        return _to_domain(EventTypeDutyConfiguration, row)

    async def delete_configuration(self, district_id, congregation_id, category_id):
        await self.session.execute(
            delete(EventTypeDutyConfigurationORM).where(
                EventTypeDutyConfigurationORM.district_id == district_id,
                EventTypeDutyConfigurationORM.congregation_id == congregation_id,
                EventTypeDutyConfigurationORM.duty_category_id == category_id,
            )
        )

    async def get_assignment(self, assignment_id):
        row = await self.session.get(EventDutyAssignmentORM, assignment_id)
        return _to_domain(EventDutyAssignment, row) if row else None

    async def lock_assignment(self, assignment_id):
        row = await self.session.scalar(
            select(EventDutyAssignmentORM)
            .where(EventDutyAssignmentORM.id == assignment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return _to_domain(EventDutyAssignment, row) if row else None

    async def eligible_users(self, district_id, congregation_id):
        rows = await self.session.execute(
            text(
                "SELECT sub, display_name FROM eligible_duty_users(:district_id, :congregation_id)"
            ),
            {"district_id": district_id, "congregation_id": congregation_id},
        )
        return [dict(row) for row in rows.mappings().all()]

    async def eligible_user_display_name(self, district_id, congregation_id, user_sub):
        return await self.session.scalar(
            text(
                "SELECT display_name FROM eligible_duty_users(:district_id, :congregation_id) "
                "WHERE sub = :user_sub"
            ),
            {
                "district_id": district_id,
                "congregation_id": congregation_id,
                "user_sub": user_sub,
            },
        )

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
        statement = insert(DutyNameSuggestionORM).values(**values)
        conflict_columns = [
            "district_id",
            "congregation_id",
            "duty_category_id",
            "normalized_name",
        ]
        statement = (
            statement.on_conflict_do_update(
                index_elements=conflict_columns,
                set_={"hidden": False, "display_name": values["display_name"]},
            )
            if activate
            else statement.on_conflict_do_nothing(index_elements=conflict_columns)
        ).returning(DutyNameSuggestionORM)
        row = await self.session.scalar(statement)
        if row is None:
            row = await self.session.scalar(
                select(DutyNameSuggestionORM).where(
                    DutyNameSuggestionORM.district_id == district_id,
                    DutyNameSuggestionORM.congregation_id == congregation_id,
                    DutyNameSuggestionORM.duty_category_id == category_id,
                    DutyNameSuggestionORM.normalized_name == values["normalized_name"],
                )
            )
        return _to_domain(DutyNameSuggestion, row)

    async def get_suggestion(self, suggestion_id):
        row = await self.session.get(DutyNameSuggestionORM, suggestion_id)
        return _to_domain(DutyNameSuggestion, row) if row else None

    async def lock_suggestion(self, suggestion_id):
        row = await self.session.scalar(
            select(DutyNameSuggestionORM)
            .where(DutyNameSuggestionORM.id == suggestion_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return _to_domain(DutyNameSuggestion, row) if row else None

    async def list_suggestions(self, district_id, congregation_id, category_id):
        rows = (
            await self.session.scalars(
                select(DutyNameSuggestionORM)
                .where(
                    DutyNameSuggestionORM.district_id == district_id,
                    DutyNameSuggestionORM.congregation_id == congregation_id,
                    DutyNameSuggestionORM.duty_category_id == category_id,
                )
                .order_by(DutyNameSuggestionORM.normalized_name)
            )
        ).all()
        return [_to_domain(DutyNameSuggestion, row) for row in rows]

    async def save_suggestion(self, suggestion):
        row = await self.session.get(DutyNameSuggestionORM, suggestion.id)
        if row is None:
            raise ValueError("Suggestion not found")
        for field in fields(suggestion):
            setattr(row, field.name, getattr(suggestion, field.name))
        await self.session.flush()
        return _to_domain(DutyNameSuggestion, row)

    async def delete_assignment(self, assignment_id):
        row = await self.session.get(EventDutyAssignmentORM, assignment_id)
        if row:
            slot = await self.session.get(PlanningSlotORM, row.planning_slot_id)
            slot.updated_at = datetime.now(UTC)
            await self.session.delete(row)
            await self.session.flush()
