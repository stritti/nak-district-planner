"""Phase 2: calendar_integrations table + extend events for external sync

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-03 00:00:00.000000

Changes:
- New ENUM: calendar_type (GOOGLE, MICROSOFT, CALDAV, ICS)
- New table: calendar_integrations
- Extend event_status ENUM: add CANCELLED value
- Extend events table: external_uid, calendar_integration_id, content_hash
- Unique index on (calendar_integration_id, external_uid) for sync deduplication
- Index on calendar_integrations.district_id
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- New ENUM: calendar_type ---
    calendar_type = postgresql.ENUM("GOOGLE", "MICROSOFT", "CALDAV", "ICS", name="calendar_type")
    calendar_type.create(op.get_bind(), checkfirst=True)

    # --- New table: calendar_integrations ---
    op.create_table(
        "calendar_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "district_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("districts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", postgresql.ENUM(name="calendar_type", create_type=False), nullable=False),
        sa.Column("credentials_enc", sa.Text, nullable=False),
        sa.Column("sync_interval", sa.Integer, nullable=False, server_default="60"),
        sa.Column(
            "capabilities",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_calendar_integrations_district_id",
        "calendar_integrations",
        ["district_id"],
    )

    # --- Extend event_status ENUM: add CANCELLED ---
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction; Alembic handles
    # this correctly because PostgreSQL auto-commits DDL for ENUM alterations.
    op.execute("ALTER TYPE event_status ADD VALUE IF NOT EXISTS 'CANCELLED'")

    # --- Extend events table with external sync columns ---
    op.add_column("events", sa.Column("external_uid", sa.String(500), nullable=True))
    op.add_column(
        "events",
        sa.Column(
            "calendar_integration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calendar_integrations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("events", sa.Column("content_hash", sa.String(64), nullable=True))

    # Unique partial index for deduplication: one event per (integration, uid)
    op.execute(
        """
        CREATE UNIQUE INDEX ix_events_external_uid
        ON events (calendar_integration_id, external_uid)
        WHERE external_uid IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_events_external_uid")
    op.drop_column("events", "content_hash")
    op.drop_column("events", "calendar_integration_id")
    op.drop_column("events", "external_uid")

    # Note: removing an ENUM value is not supported in PostgreSQL directly.
    # Downgrade leaves 'CANCELLED' in the event_status ENUM; it is harmless.

    op.drop_index("ix_calendar_integrations_district_id", table_name="calendar_integrations")
    op.drop_table("calendar_integrations")
    postgresql.ENUM(name="calendar_type").drop(op.get_bind(), checkfirst=True)
