"""Initial schema: districts, congregations, events, service_assignments

Revision ID: 0001
Revises:
Create Date: 2026-03-02 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ENUMs (must exist before columns reference them) ---
    event_source = postgresql.ENUM("INTERNAL", "EXTERNAL", name="event_source")
    event_status = postgresql.ENUM("DRAFT", "PUBLISHED", name="event_status")
    event_visibility = postgresql.ENUM("INTERNAL", "PUBLIC", name="event_visibility")
    assignment_status = postgresql.ENUM("OPEN", "ASSIGNED", "CONFIRMED", name="assignment_status")

    event_source.create(op.get_bind(), checkfirst=True)
    event_status.create(op.get_bind(), checkfirst=True)
    event_visibility.create(op.get_bind(), checkfirst=True)
    assignment_status.create(op.get_bind(), checkfirst=True)

    # --- districts ---
    op.create_table(
        "districts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- congregations ---
    op.create_table(
        "congregations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "district_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- events ---
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.Column("source", postgresql.ENUM(name="event_source", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM(name="event_status", create_type=False), nullable=False),
        sa.Column("visibility", postgresql.ENUM(name="event_visibility", create_type=False), nullable=False),
        sa.Column("audiences", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column(
            "applicability",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- service_assignments ---
    op.create_table(
        "service_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("leader_name", sa.String(255), nullable=False),
        sa.Column("status", postgresql.ENUM(name="assignment_status", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("service_assignments")
    op.drop_table("events")
    op.drop_table("congregations")
    op.drop_table("districts")

    postgresql.ENUM(name="assignment_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="event_visibility").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="event_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="event_source").drop(op.get_bind(), checkfirst=True)
