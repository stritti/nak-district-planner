"""Remove legacy events table, add M3 sync fields to event_instances.

M3 — Sync Algorithm Hardening:
  - Add sync_state, external_uid, content_hash, calendar_integration_id,
    last_external_modified_at, last_internal_modified_at to event_instances
  - Create external_event_links table
  - Drop FK constraints referencing events.id
  - Drop the legacy events table

Revision ID: 0125
Revises: 0124
Create Date: 2026-06-25 20:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0125"
down_revision: str | None = "0124"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 0. Create sync_state enum type before adding columns ──
    postgresql.ENUM(
        "CLEAN",
        "DIRTY_INTERNAL",
        "DIRTY_EXTERNAL",
        "CONFLICT",
        name="sync_state",
    ).create(op.get_bind(), checkfirst=True)

    # ── 1. Add M3 sync fields to event_instances ──
    op.add_column(
        "event_instances",
        sa.Column(
            "sync_state",
            postgresql.ENUM(
                "CLEAN",
                "DIRTY_INTERNAL",
                "DIRTY_EXTERNAL",
                "CONFLICT",
                name="sync_state",
                create_type=False,
            ),
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
        sa.Column("calendar_integration_id", sa.Uuid(), nullable=False),
        sa.Column("last_synced_hash", sa.String(64), nullable=True),
        sa.Column("revision_marker", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_instance_id"],
            ["event_instances.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["calendar_integration_id"],
            ["calendar_integrations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_external_event_links_provider_integration_event",
        "external_event_links",
        ["provider", "external_event_id", "calendar_integration_id"],
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
        "fk_planning_slots_invitation_source_event_id_events",
        "planning_slots",
        type_="foreignkey",
    )
    # invitation_overwrite_requests.source_event_id, target_event_id
    op.drop_constraint(
        "invitation_overwrite_requests_source_event_id_fkey",
        "invitation_overwrite_requests",
        type_="foreignkey",
    )
    op.drop_constraint(
        "invitation_overwrite_requests_target_event_id_fkey",
        "invitation_overwrite_requests",
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

    # ── 4. Migrate events data to planning_slots + event_instances ──
    op.execute(
        """
        INSERT INTO planning_slots (id, district_id, planning_date, planning_time,
            congregation_id, category, title, status, approval_status,
            invitation_source_congregation_id, invitation_source_event_id,
            applicability, created_at, updated_at)
        SELECT gen_random_uuid(), district_id, start_at::date, start_at::time,
            congregation_id, category, title,
            CASE WHEN status = 'CANCELLED' THEN 'CANCELLED'::planning_slot_status ELSE 'ACTIVE'::planning_slot_status END,
            COALESCE(approval_status, 'PLANNED'::event_approval_status),
            invitation_source_congregation_id, id,
            applicability, created_at, updated_at
        FROM events
        """
    )
    op.execute(
        """
        INSERT INTO event_instances (id, planning_slot_id, title, description,
            actual_start_at, actual_end_at, source, visibility,
            deviation_flag, sync_state,
            external_uid, content_hash, calendar_integration_id,
            created_at, updated_at)
        SELECT gen_random_uuid(), ps.id, COALESCE(e.title, ''), e.description,
            e.start_at, e.end_at, e.source, e.visibility,
            FALSE, 'CLEAN'::sync_state,
            e.external_uid, e.content_hash, e.calendar_integration_id,
            e.created_at, e.updated_at
        FROM events e
        JOIN planning_slots ps ON ps.invitation_source_event_id = e.id
        """
    )
    op.execute(
        """
        INSERT INTO external_event_links (id, event_instance_id, provider,
            external_event_id, calendar_integration_id, last_synced_hash,
            created_at, updated_at)
        SELECT gen_random_uuid(), ei.id, COALESCE(ci.type, 'GOOGLE'),
            e.external_uid, e.calendar_integration_id, e.content_hash,
            now(), now()
        FROM events e
        JOIN planning_slots ps ON ps.invitation_source_event_id = e.id
        JOIN event_instances ei ON ei.planning_slot_id = ps.id
        LEFT JOIN calendar_integrations ci ON ci.id = e.calendar_integration_id
        WHERE e.external_uid IS NOT NULL
          AND e.calendar_integration_id IS NOT NULL
        """
    )

    # ── 5. Drop the legacy events table ──
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
        "fk_planning_slots_invitation_source_event_id_events",
        "planning_slots",
        "events",
        ["invitation_source_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "invitation_overwrite_requests_source_event_id_fkey",
        "invitation_overwrite_requests",
        "events",
        ["source_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "invitation_overwrite_requests_target_event_id_fkey",
        "invitation_overwrite_requests",
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
    op.drop_index("ix_external_event_links_provider_integration_event", table_name="external_event_links")
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
    postgresql.ENUM(name="sync_state").drop(op.get_bind(), checkfirst=True)
