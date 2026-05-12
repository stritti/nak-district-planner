"""Add invitation workflow tables and fields.

Revision ID: b15c9d3e4f21
Revises: ae6c055cc050
Create Date: 2026-04-07 12:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b15c9d3e4f21"
down_revision: str | None = "ae6c055cc050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    invitation_target_type = postgresql.ENUM(
        "DISTRICT_CONGREGATION",
        "EXTERNAL_NOTE",
        name="invitation_target_type",
    )
    overwrite_decision_status = postgresql.ENUM(
        "PENDING_OVERWRITE",
        "ACCEPTED",
        "REJECTED",
        name="overwrite_decision_status",
    )
    invitation_target_type.create(op.get_bind(), checkfirst=True)
    overwrite_decision_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "events",
        sa.Column(
            "invitation_source_congregation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "invitation_source_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.add_column(
        "congregations",
        sa.Column(
            "invitation_target_type",
            postgresql.ENUM(name="invitation_target_type", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "congregations",
        sa.Column(
            "invitation_target_congregation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "congregations",
        sa.Column("invitation_external_note", sa.String(500), nullable=True),
    )

    op.create_table(
        "congregation_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_congregation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_type",
            postgresql.ENUM(name="invitation_target_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "target_congregation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_target_note", sa.String(500), nullable=True),
        sa.Column(
            "linked_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_congregation_invitations_source_event",
        "congregation_invitations",
        ["source_event_id"],
    )
    op.create_index(
        "ix_congregation_invitations_target_congregation",
        "congregation_invitations",
        ["target_congregation_id"],
    )

    op.create_table(
        "invitation_overwrite_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invitation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("congregation_invitations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proposed_title", sa.String(500), nullable=False),
        sa.Column("proposed_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposed_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proposed_description", sa.Text, nullable=True),
        sa.Column("proposed_category", sa.String(255), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="overwrite_decision_status", create_type=False),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_invitation_overwrite_requests_source_event",
        "invitation_overwrite_requests",
        ["source_event_id"],
    )
    op.create_index(
        "ix_invitation_overwrite_requests_target_event",
        "invitation_overwrite_requests",
        ["target_event_id"],
    )
    op.create_index(
        "ix_invitation_overwrite_requests_status",
        "invitation_overwrite_requests",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_invitation_overwrite_requests_status", table_name="invitation_overwrite_requests"
    )
    op.drop_index(
        "ix_invitation_overwrite_requests_target_event", table_name="invitation_overwrite_requests"
    )
    op.drop_index(
        "ix_invitation_overwrite_requests_source_event", table_name="invitation_overwrite_requests"
    )
    op.drop_table("invitation_overwrite_requests")

    op.drop_index(
        "ix_congregation_invitations_target_congregation", table_name="congregation_invitations"
    )
    op.drop_index("ix_congregation_invitations_source_event", table_name="congregation_invitations")
    op.drop_table("congregation_invitations")

    op.drop_column("congregations", "invitation_external_note")
    op.drop_column("congregations", "invitation_target_congregation_id")
    op.drop_column("congregations", "invitation_target_type")

    op.drop_column("events", "invitation_source_event_id")
    op.drop_column("events", "invitation_source_congregation_id")

    postgresql.ENUM(name="overwrite_decision_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="invitation_target_type").drop(op.get_bind(), checkfirst=True)
