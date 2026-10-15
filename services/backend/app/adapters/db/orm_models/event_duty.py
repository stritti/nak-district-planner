# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Persistence for scoped duty definitions, snapshots and remembered names."""

from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class EventDutyCategoryORM(Base):
    __tablename__ = "event_duty_categories"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_duty_category_capacity"),
        Index(
            "uq_duty_category_scope_code",
            "district_id",
            "congregation_id",
            "code",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"))
    congregation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("congregations.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(255))
    event_categories: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    capacity: Mapped[int] = mapped_column(Integer, default=1)


class EventTypeDutyConfigurationORM(Base):
    __tablename__ = "event_type_duty_configurations"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_duty_configuration_capacity"),
        Index("uq_duty_configuration_scope", "congregation_id", "duty_category_id", unique=True),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"))
    congregation_id: Mapped[UUID] = mapped_column(
        ForeignKey("congregations.id", ondelete="CASCADE")
    )
    duty_category_id: Mapped[UUID] = mapped_column(
        ForeignKey("event_duty_categories.id", ondelete="CASCADE")
    )
    event_categories: Mapped[list[str]] = mapped_column(ARRAY(String(255)), default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    capacity: Mapped[int] = mapped_column(Integer, default=1)


class DutyNameSuggestionORM(Base):
    __tablename__ = "duty_name_suggestions"
    __table_args__ = (
        Index(
            "uq_duty_suggestion_identity",
            "district_id",
            "congregation_id",
            "duty_category_id",
            "normalized_name",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    district_id: Mapped[UUID] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"))
    congregation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("congregations.id", ondelete="CASCADE")
    )
    duty_category_id: Mapped[UUID] = mapped_column(
        ForeignKey("event_duty_categories.id", ondelete="RESTRICT")
    )
    display_name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255))
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)


class EventDutyAssignmentORM(Base):
    __tablename__ = "event_duty_assignments"
    __table_args__ = (
        CheckConstraint(
            "(linked_user_sub IS NOT NULL AND normalized_name IS NULL) OR (linked_user_sub IS NULL AND normalized_name IS NOT NULL)",
            name="ck_duty_assignment_identity",
        ),
        Index(
            "uq_duty_assignment_subject",
            "planning_slot_id",
            "duty_category_id",
            "linked_user_sub",
            unique=True,
            postgresql_where=text("linked_user_sub IS NOT NULL"),
        ),
        Index(
            "uq_duty_assignment_name",
            "planning_slot_id",
            "duty_category_id",
            "normalized_name",
            unique=True,
            postgresql_where=text("linked_user_sub IS NULL"),
        ),
        Index("ix_duty_assignments_slot", "planning_slot_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    planning_slot_id: Mapped[UUID] = mapped_column(
        ForeignKey("planning_slots.id", ondelete="CASCADE")
    )
    duty_category_id: Mapped[UUID] = mapped_column(
        ForeignKey("event_duty_categories.id", ondelete="RESTRICT")
    )
    district_id: Mapped[UUID] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"))
    congregation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("congregations.id", ondelete="RESTRICT")
    )
    display_name: Mapped[str] = mapped_column(String(255))
    duty_label: Mapped[str] = mapped_column(String(255))
    linked_user_sub: Mapped[str | None] = mapped_column(
        String(512), ForeignKey("users.sub", ondelete="RESTRICT")
    )
    normalized_name: Mapped[str | None] = mapped_column(String(255))
    suggestion_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("duty_name_suggestions.id", ondelete="SET NULL")
    )
