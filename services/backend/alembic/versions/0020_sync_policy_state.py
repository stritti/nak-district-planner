# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Persist calendar deletion policy and explicit sync tombstone state."""

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("external_event_links_event_instance_id_fkey", "external_event_links", type_="foreignkey")
    op.create_foreign_key(
        "external_event_links_event_instance_id_fkey", "external_event_links", "event_instances",
        ["event_instance_id"], ["id"], ondelete="CASCADE"
    )
    op.add_column(
        "calendar_integrations",
        sa.Column(
            "delete_behavior",
            sa.String(length=32),
            nullable=False,
            server_default="MARK_CANCELLED",
        ),
    )
    op.add_column(
        "external_event_links",
        sa.Column("state", sa.String(length=32), nullable=False, server_default="ACTIVE"),
    )
    op.add_column(
        "external_event_links",
        sa.Column("last_synced_payload", sa.JSON(), nullable=True),
    )
    op.add_column(
        "external_event_links",
        sa.Column("provider_resource_id", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "external_event_links",
        sa.Column("deletion_origin", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "external_event_links",
        sa.Column("deletion_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "external_event_links",
        sa.Column("tombstoned_at", sa.DateTime(timezone=True), nullable=True),
    )
    # 0019 represented sync tombstones implicitly. Preserve those rows while
    # migrating to an explicit state so unrelated SET NULL operations are not
    # mistaken for synchronization intent.
    op.execute(
        """
        UPDATE external_event_links
        SET state = 'SYNC_TOMBSTONE',
            deletion_origin = 'EXTERNAL',
            deletion_reason = 'migrated-0019',
            tombstoned_at = updated_at
        WHERE event_instance_id IS NULL
        """
    )
    op.alter_column("calendar_integrations", "delete_behavior", server_default=None)
    op.alter_column("external_event_links", "state", server_default=None)


def downgrade():
    op.drop_constraint("external_event_links_event_instance_id_fkey", "external_event_links", type_="foreignkey")
    op.create_foreign_key(
        "external_event_links_event_instance_id_fkey", "external_event_links", "event_instances",
        ["event_instance_id"], ["id"], ondelete="SET NULL"
    )
    op.drop_column("external_event_links", "tombstoned_at")
    op.drop_column("external_event_links", "deletion_reason")
    op.drop_column("external_event_links", "deletion_origin")
    op.drop_column("external_event_links", "provider_resource_id")
    op.drop_column("external_event_links", "last_synced_payload")
    op.drop_column("external_event_links", "state")
    op.drop_column("calendar_integrations", "delete_behavior")
