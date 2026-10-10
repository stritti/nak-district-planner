# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Retain sync mappings after hard deletion to prevent re-import loops."""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("external_event_links_event_instance_id_fkey", "external_event_links", type_="foreignkey")
    op.alter_column("external_event_links", "event_instance_id", existing_type=sa.UUID(), nullable=True)
    op.create_foreign_key("external_event_links_event_instance_id_fkey", "external_event_links", "event_instances", ["event_instance_id"], ["id"], ondelete="SET NULL")


def downgrade():
    op.execute("DELETE FROM external_event_links WHERE event_instance_id IS NULL")
    op.drop_constraint("external_event_links_event_instance_id_fkey", "external_event_links", type_="foreignkey")
    op.alter_column("external_event_links", "event_instance_id", existing_type=sa.UUID(), nullable=False)
    op.create_foreign_key("external_event_links_event_instance_id_fkey", "external_event_links", "event_instances", ["event_instance_id"], ["id"], ondelete="CASCADE")
