# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Persistence contract for the monthly recurring-event checklist."""

from __future__ import annotations

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.adapters.db.orm_models.recurring_event import (
    RecurringEventDecisionORM,
    RecurringEventTemplateORM,
)


def test_recurring_template_has_tenant_scoped_foreign_key() -> None:
    table = RecurringEventTemplateORM.__table__
    matching = [
        fk for fk in table.foreign_key_constraints
        if {column.name for column in fk.columns} == {"congregation_id", "district_id"}
    ]
    assert len(matching) == 1
    assert matching[0].referred_table.name == "congregations"
    assert "uq_recurring_templates_id_district" in {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_decision_has_stable_unique_occurrence_and_same_district_slot_fk() -> None:
    table = RecurringEventDecisionORM.__table__
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {col.name for col in constraint.columns} == {
            "template_id", "occurrence_local_date"
        }
        for constraint in table.constraints
    )
    scoped = [
        constraint for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
        and {column.name for column in constraint.columns} == {"planning_slot_id", "district_id"}
    ]
    assert len(scoped) == 1
    assert scoped[0].ondelete == "SET NULL (planning_slot_id)"


def test_decision_slot_is_nullable_but_its_district_is_not() -> None:
    cols = RecurringEventDecisionORM.__table__.columns
    assert cols["planning_slot_id"].nullable
    assert not cols["district_id"].nullable
