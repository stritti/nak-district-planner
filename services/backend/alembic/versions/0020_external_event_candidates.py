"""Persist external events pending review."""

from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
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
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("matched_slot_id", sa.UUID(), sa.ForeignKey("planning_slots.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("calendar_integration_id", "external_event_id"),
        sa.CheckConstraint("end_at >= start_at"),
    )
    op.create_index("ix_external_candidates_district_status", "external_event_candidates", ["district_id", "status"])


def downgrade():
    op.drop_table("external_event_candidates")
