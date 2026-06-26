"""Remove legacy events table, add M3 sync fields to event_instances.

M3 — Sync Algorithm Hardening:
  - Add sync_state, external_uid, content_hash, calendar_integration_id,
    last_external_modified_at, last_internal_modified_at to event_instances
  - Create external_event_links table
  - Drop FK constraints referencing events.id
  - Drop the legacy events table

Revision ID: 0125_remove_events_add_sync_fields
Revises: 0124_create_notifications_table
Create Date: 2026-06-25 20:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0125_remove_events_add_sync_fields"
down_revision: str | None = "0124_create_notifications_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Add M3 sync fields to event_instances ──
    op.add_column(
        "event_instances",
        sa.Column(
            "sync_state",
            sa.Enum("CLEAN", "DIRTY_INTERNAL", "DIRTY_EXTERNAL", "CONFLICT", name="sync_state"),
            nullable=False,
            server_default="CLEAN",
        ),
    )
    op.add_column(
        "event_instances",
        sa.Column("external_uid", sa.String(500), nullable=True),
    )
    op.add_column(
        "event_instances",
        sa.Column("content_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "event_instances",
        sa.Column("calendar_integration_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_event_instances_calendar_integration_id",
        "event_instances",
        "calendar_integrations",
        ["calendar_integration_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "event_instances",
        sa.Column("last_external_modified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "event_instances",
        sa.Column("last_internal_modified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 2. Create external_event_links table ──
    op.create_table(
        "external_event_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_instance_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("external_event_id", sa.String(500), nullable=False),
        sa.Column("last_synced_hash", sa.String(64), nullable=True),
        sa.Column("revision_marker", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_instance_id"],
            ["event_instances.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_event_links_provider_event",
        "external_event_links",
        ["provider", "external_event_id"],
        unique=True,
    )

    # ── 3. Drop FK constraints referencing events.id ──
    # service_assignments.event_id
    op.drop_constraint(
        "service_assignments_event_id_fkey",
        "service_assignments",
        type_="foreignkey",
    )
    # planning_slots.invitation_source_event_id
    op.drop_constraint(
        "planning_slots_invitation_source_event_id_fkey",
        "planning_slots",
        type_="foreignkey",
    )
    # invitation_overwrite_request.source_event_id, target_event_id
    op.drop_constraint(
        "invitation_overwrite_request_source_event_id_fkey",
        "invitation_overwrite_request",
        type_="foreignkey",
    )
    op.drop_constraint(
        "invitation_overwrite_request_target_event_id_fkey",
        "invitation_overwrite_request",
        type_="foreignkey",
    )
    # congregation_invitations.source_event_id, linked_event_id
    op.drop_constraint(
        "congregation_invitations_source_event_id_fkey",
        "congregation_invitations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "congregation_invitations_linked_event_id_fkey",
        "congregation_invitations",
        type_="foreignkey",
    )

    # ── 4. Drop the legacy events table ──
    op.drop_table("events")


def downgrade() -> None:
    # ── Reverse 4: Recreate events table ──
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("district_id", sa.Uuid(), nullable=False),
        sa.Column("congregation_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("visibility", sa.String(20), nullable=False),
        sa.Column("audiences", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("applicability", sa.ARRAY(sa.Uuid()), nullable=False, server_default="{}"),
        sa.Column("approval_status", sa.String(20), nullable=True),
        sa.Column("external_uid", sa.String(500), nullable=True),
        sa.Column("calendar_integration_id", sa.Uuid(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("generation_slot_key", sa.String(100), nullable=True),
        sa.Column("invitation_source_congregation_id", sa.Uuid(), nullable=True),
        sa.Column("invitation_source_event_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Reverse 3: Restore FK constraints ──
    op.create_foreign_key(
        "service_assignments_event_id_fkey",
        "service_assignments",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "planning_slots_invitation_source_event_id_fkey",
        "planning_slots",
        "events",
        ["invitation_source_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "invitation_overwrite_request_source_event_id_fkey",
        "invitation_overwrite_request",
        "events",
        ["source_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "invitation_overwrite_request_target_event_id_fkey",
        "invitation_overwrite_request",
        "events",
        ["target_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "congregation_invitations_source_event_id_fkey",
        "congregation_invitations",
        "events",
        ["source_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "congregation_invitations_linked_event_id_fkey",
        "congregation_invitations",
        "events",
        ["linked_event_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── Reverse 2: Drop external_event_links table ──
    op.drop_index("ix_external_event_links_provider_event", table_name="external_event_links")
    op.drop_table("external_event_links")

    # ── Reverse 1: Remove M3 sync fields from event_instances ──
    op.drop_constraint(
        "fk_event_instances_calendar_integration_id",
        "event_instances",
        type_="foreignkey",
    )
    op.drop_column("event_instances", "last_internal_modified_at")
    op.drop_column("event_instances", "last_external_modified_at")
    op.drop_column("event_instances", "calendar_integration_id")
    op.drop_column("event_instances", "content_hash")
    op.drop_column("event_instances", "external_uid")
    op.drop_column("event_instances", "sync_state")
    sa.Enum(name="sync_state").drop(op.get_bind())
