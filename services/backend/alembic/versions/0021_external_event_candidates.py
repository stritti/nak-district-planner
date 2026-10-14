# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Persist external event candidates after the sync-policy migration."""

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "external_event_candidates",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("district_id", sa.UUID(), sa.ForeignKey("districts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calendar_integration_id", sa.UUID(), sa.ForeignKey("calendar_integrations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_event_id", sa.String(500), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("congregation_id", sa.UUID(), sa.ForeignKey("congregations.id", ondelete="SET NULL")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category", sa.String(255)),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("revision_marker", sa.String(500)),
        sa.Column("provider_resource_id", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("matched_slot_id", sa.UUID(), sa.ForeignKey("planning_slots.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("calendar_integration_id", "external_event_id"),
        sa.CheckConstraint("end_at > start_at", name="ck_external_candidates_positive_duration"),
    )
    op.create_index("ix_external_candidates_district_status", "external_event_candidates", ["district_id", "status"])


def downgrade():
    op.drop_index("ix_external_candidates_district_status", table_name="external_event_candidates")
    op.drop_table("external_event_candidates")
