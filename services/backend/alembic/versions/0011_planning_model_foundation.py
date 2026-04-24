"""Add planning model foundation tables for prospective rollout.

Revision ID: 0011_planning_model_foundation
Revises: 0010_leader_registrations
Create Date: 2026-04-06 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_planning_model_foundation"
down_revision: str | None = "0010_leader_registrations"


def upgrade() -> None:
    planning_slot_status = postgresql.ENUM(
        "ACTIVE",
        "CANCELLED",
        name="planning_slot_status",
    )
    planning_slot_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "planning_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "district_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "congregation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("default_planning_time", sa.Time(), nullable=False),
        sa.Column(
            "recurrence_pattern",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("active_from", sa.Date(), nullable=True),
        sa.Column("active_until", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "planning_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "series_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("planning_series.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "district_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "congregation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("planning_date", sa.Date(), nullable=False),
        sa.Column("planning_time", sa.Time(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="planning_slot_status", create_type=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_planning_slots_district_date",
        "planning_slots",
        ["district_id", "planning_date"],
    )
    op.create_index(
        "ix_planning_slots_congregation_date",
        "planning_slots",
        ["congregation_id", "planning_date"],
    )

    op.create_table(
        "event_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "planning_slot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("planning_slots.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("actual_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", postgresql.ENUM(name="event_source", create_type=False), nullable=False),
        sa.Column("visibility", postgresql.ENUM(name="event_visibility", create_type=False), nullable=False),
        sa.Column("deviation_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.add_column(
        "service_assignments",
        sa.Column("planning_slot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_service_assignments_planning_slot_id",
        "service_assignments",
        "planning_slots",
        ["planning_slot_id"],
        ["id"],
        ondelete="CASCADE",
    )

def downgrade() -> None:
    op.drop_constraint(
        "fk_service_assignments_planning_slot_id",
        "service_assignments",
        type_="foreignkey",
    )
    op.drop_column("service_assignments", "planning_slot_id")
    op.drop_table("event_instances")
    op.drop_index("ix_planning_slots_congregation_date", table_name="planning_slots")
    op.drop_index("ix_planning_slots_district_date", table_name="planning_slots")
    op.drop_table("planning_slots")
    op.drop_table("planning_series")
    postgresql.ENUM(name="planning_slot_status").drop(op.get_bind(), checkfirst=True)
