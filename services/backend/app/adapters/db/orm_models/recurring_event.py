# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Tenant-constrained recurring template and per-occurrence decision rows."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.db.base import Base


class RecurringEventTemplateORM(Base):
    __tablename__ = "recurring_event_templates"
    __table_args__ = (
        UniqueConstraint("id", "district_id", name="uq_recurring_templates_id_district"),
        ForeignKeyConstraint(
            ("congregation_id", "district_id"),
            ("congregations.id", "congregations.district_id"),
            name="fk_recurring_templates_congregation_scope",
            ondelete="CASCADE",
        ),
        CheckConstraint("duration_minutes > 0", name="ck_recurring_template_duration"),
        CheckConstraint("revision > 0", name="ck_recurring_template_revision"),
        CheckConstraint(
            "active_until IS NULL OR active_from IS NULL OR active_until >= active_from",
            name="ck_recurring_template_active_range",
        ),
        Index("ix_recurring_templates_district_scope", "district_id", "congregation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    congregation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    recurrence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    applicability: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)), nullable=False, default=list, server_default=text("'{}'::varchar[]")
    )
    excluded_dates: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    active_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    active_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Europe/Berlin"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RecurringEventDecisionORM(Base):
    __tablename__ = "recurring_event_decisions"
    __table_args__ = (
        UniqueConstraint(
            "template_id", "occurrence_local_date", name="uq_recurring_decision_occurrence"
        ),
        UniqueConstraint("planning_slot_id", name="uq_recurring_decisions_planning_slot"),
        ForeignKeyConstraint(
            ("template_id", "district_id"),
            ("recurring_event_templates.id", "recurring_event_templates.district_id"),
            name="fk_recurring_decisions_template_scope",
            ondelete="CASCADE",
        ),
        # PostgreSQL 15+ column-scoped SET NULL preserves the immutable district ID.
        ForeignKeyConstraint(
            ("planning_slot_id", "district_id"),
            ("planning_slots.id", "planning_slots.district_id"),
            name="fk_recurring_decisions_slot_scope",
            ondelete="SET NULL (planning_slot_id)",
        ),
        CheckConstraint(
            "status IN ('ACCEPTED', 'SKIPPED')", name="ck_recurring_decision_status"
        ),
        CheckConstraint(
            "status != 'SKIPPED' OR planning_slot_id IS NULL",
            name="ck_recurring_decision_skipped_slot",
        ),
        Index("ix_recurring_decisions_district_date", "district_id", "occurrence_local_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    district_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    occurrence_local_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    planning_slot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
