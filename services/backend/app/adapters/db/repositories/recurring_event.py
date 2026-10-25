# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""SQLAlchemy adapter for opt-in recurring templates and durable decisions.

Mutating methods flush but never commit; the request transaction owns atomicity.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import and_, any_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.orm_models.recurring_event import (
    RecurringEventDecisionORM,
    RecurringEventTemplateORM,
)
from app.domain.models.recurring_event_template import (
    DecisionStatus,
    RecurrenceKind,
    RecurrenceRule,
    RecurringEventDecision,
    RecurringEventTemplate,
)


def _rule_to_json(rule: RecurrenceRule) -> dict:
    return {
        "version": rule.version,
        "kind": rule.kind.value,
        "anchor_date": rule.anchor_date.isoformat(),
        "interval": rule.interval,
        "weekdays": list(rule.weekdays),
        "day_of_month": rule.day_of_month,
        "weekday": rule.weekday,
        "ordinal": rule.ordinal,
    }


def _rule_from_json(data: dict) -> RecurrenceRule:
    return RecurrenceRule(
        kind=RecurrenceKind(data["kind"]),
        anchor_date=date.fromisoformat(data["anchor_date"]),
        interval=data.get("interval", 1),
        weekdays=tuple(data.get("weekdays") or ()),
        day_of_month=data.get("day_of_month"),
        weekday=data.get("weekday"),
        ordinal=data.get("ordinal"),
        version=data.get("version", 1),
    )


def _template_from_row(row: RecurringEventTemplateORM) -> RecurringEventTemplate:
    return RecurringEventTemplate(
        id=row.id,
        district_id=row.district_id,
        congregation_id=row.congregation_id,
        title=row.title,
        description=row.description,
        category=row.category,
        start_time=row.start_time,
        duration_minutes=row.duration_minutes,
        recurrence=_rule_from_json(row.recurrence),
        applicability=tuple(row.applicability or ()),
        excluded_dates=tuple(date.fromisoformat(value) for value in (row.excluded_dates or ())),
        active_from=row.active_from,
        active_until=row.active_until,
        is_active=row.is_active,
        revision=row.revision,
        timezone=row.timezone,
    )


def _template_to_row(entry: RecurringEventTemplate, row: RecurringEventTemplateORM) -> None:
    row.id = entry.id
    row.district_id = entry.district_id
    row.congregation_id = entry.congregation_id
    row.title = entry.title
    row.description = entry.description
    row.category = entry.category
    row.start_time = entry.start_time
    row.duration_minutes = entry.duration_minutes
    row.recurrence = _rule_to_json(entry.recurrence)
    row.applicability = list(entry.applicability)
    row.excluded_dates = [value.isoformat() for value in entry.excluded_dates]
    row.active_from = entry.active_from
    row.active_until = entry.active_until
    row.is_active = entry.is_active
    row.revision = entry.revision
    row.timezone = entry.timezone
    now = datetime.now(UTC)
    row.created_at = row.created_at or now
    row.updated_at = now


def _decision_from_row(row: RecurringEventDecisionORM) -> RecurringEventDecision:
    return RecurringEventDecision(
        id=row.id,
        district_id=row.district_id,
        template_id=row.template_id,
        occurrence_local_date=row.occurrence_local_date,
        status=DecisionStatus(row.status),
        planning_slot_id=row.planning_slot_id,
        created_by=row.created_by,
    )


class SqlRecurringEventRepository:
    """Transaction-scoped repository; RLS is a second line of tenant isolation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_template(
        self, template_id: uuid.UUID, *, for_update: bool = False
    ) -> RecurringEventTemplate | None:
        row = await self.session.get(
            RecurringEventTemplateORM, template_id,
            with_for_update=for_update, populate_existing=for_update,
        )
        return _template_from_row(row) if row else None

    async def list_templates(self, district_id: uuid.UUID) -> list[RecurringEventTemplate]:
        result = await self.session.execute(
            select(RecurringEventTemplateORM)
            .where(RecurringEventTemplateORM.district_id == district_id)
            .order_by(RecurringEventTemplateORM.title, RecurringEventTemplateORM.id)
        )
        return [_template_from_row(row) for row in result.scalars()]

    async def list_visible_templates_page(
        self,
        district_id: uuid.UUID,
        *,
        visible_congregation_ids: set[uuid.UUID] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[RecurringEventTemplate], int]:
        """Filter at SQL level before applying the bounded list page.

        None means district-wide read access. A set limits rows to those
        belonging to the authorized congregations or distributed to them.
        """
        filters = [RecurringEventTemplateORM.district_id == district_id]
        if visible_congregation_ids is not None:
            if not visible_congregation_ids:
                return [], 0
            congregation_ids = sorted(visible_congregation_ids)
            distributed_to = or_(
                "all" == any_(RecurringEventTemplateORM.applicability),
                *(
                    str(congregation_id) == any_(RecurringEventTemplateORM.applicability)
                    for congregation_id in congregation_ids
                ),
            )
            filters.append(
                or_(
                    RecurringEventTemplateORM.congregation_id.in_(congregation_ids),
                    and_(
                        RecurringEventTemplateORM.congregation_id.is_(None),
                        distributed_to,
                    ),
                )
            )
        count_stmt = (
            select(func.count()).select_from(RecurringEventTemplateORM).where(*filters)
        )
        total = int(await self.session.scalar(count_stmt) or 0)
        result = await self.session.execute(
            select(RecurringEventTemplateORM)
            .where(*filters)
            .order_by(RecurringEventTemplateORM.title, RecurringEventTemplateORM.id)
            .limit(limit)
            .offset(offset)
        )
        return [_template_from_row(row) for row in result.scalars()], total

    async def save_template(self, entry: RecurringEventTemplate) -> None:
        row = await self.session.get(
            RecurringEventTemplateORM, entry.id, with_for_update=True
        )
        if row is None:
            row = RecurringEventTemplateORM()
            self.session.add(row)
        _template_to_row(entry, row)
        await self.session.flush()

    async def get_decision(
        self, template_id: uuid.UUID, occurrence_date: date, *, for_update: bool = False
    ) -> RecurringEventDecision | None:
        statement = select(RecurringEventDecisionORM).where(
            RecurringEventDecisionORM.template_id == template_id,
            RecurringEventDecisionORM.occurrence_local_date == occurrence_date,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        row = result.scalar_one_or_none()
        return _decision_from_row(row) if row else None

    async def list_decisions(
        self, district_id: uuid.UUID, from_date: date, to_date: date
    ) -> list[RecurringEventDecision]:
        result = await self.session.execute(
            select(RecurringEventDecisionORM).where(
                RecurringEventDecisionORM.district_id == district_id,
                RecurringEventDecisionORM.occurrence_local_date >= from_date,
                RecurringEventDecisionORM.occurrence_local_date <= to_date,
            )
        )
        return [_decision_from_row(row) for row in result.scalars()]

    async def find_slot_decision(self, slot_id: uuid.UUID) -> RecurringEventDecision | None:
        result = await self.session.execute(
            select(RecurringEventDecisionORM)
            .where(RecurringEventDecisionORM.planning_slot_id == slot_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        return _decision_from_row(row) if row else None

    async def save_decision(self, decision: RecurringEventDecision) -> None:
        row = await self.session.get(
            RecurringEventDecisionORM, decision.id, with_for_update=True
        )
        if row is None:
            row = RecurringEventDecisionORM()
            self.session.add(row)
        row.id = decision.id
        row.district_id = decision.district_id
        row.template_id = decision.template_id
        row.occurrence_local_date = decision.occurrence_local_date
        row.status = decision.status.value
        row.planning_slot_id = decision.planning_slot_id
        row.created_by = decision.created_by
        now = datetime.now(UTC)
        row.created_at = row.created_at or now
        row.updated_at = now
        await self.session.flush()

    async def delete_decision(self, decision_id: uuid.UUID) -> None:
        row = await self.session.get(
            RecurringEventDecisionORM, decision_id, with_for_update=True
        )
        if row is not None:
            await self.session.delete(row)
            await self.session.flush()
