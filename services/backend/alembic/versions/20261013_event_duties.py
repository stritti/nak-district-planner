# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Add configurable duties, minister lifecycle and subject-bound personal feeds.

Historical leaders and service assignments are preserved. All new private tables
have scoped RLS. Frozen SQL keeps this migration independent of future ORM changes.
"""

import sqlalchemy as sa

from alembic import op
from app.adapters.db.migrations.event_duty_rls import install_duty_policies, remove_duty_policies

revision = "20261013_event_duties"
down_revision = "20261012_recurring_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leaders",
        sa.Column("hidden_from_lists", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("leaders", sa.Column("service_end_date", sa.Date(), nullable=True))
    op.add_column("export_tokens", sa.Column("subject_sub", sa.String(512), nullable=True))
    op.create_foreign_key(
        "fk_export_tokens_subject",
        "export_tokens",
        "users",
        ["subject_sub"],
        ["sub"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "ck_export_tokens_subject_internal",
        "export_tokens",
        "subject_sub IS NULL OR (token_type = 'INTERNAL' AND leader_id IS NULL AND congregation_id IS NULL)",
    )
    op.execute("""CREATE TABLE event_duty_categories (
	id UUID NOT NULL,
	district_id UUID NOT NULL,
	congregation_id UUID,
	code VARCHAR(100) NOT NULL,
	label VARCHAR(255) NOT NULL,
	event_categories VARCHAR(255)[] NOT NULL,
	enabled BOOLEAN NOT NULL,
	capacity INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_duty_category_capacity CHECK (capacity > 0),
	FOREIGN KEY(district_id) REFERENCES districts (id) ON DELETE CASCADE,
	FOREIGN KEY(congregation_id) REFERENCES congregations (id) ON DELETE CASCADE
)""")
    op.execute(
        """CREATE UNIQUE INDEX uq_duty_category_scope_code ON event_duty_categories (district_id, congregation_id, code) NULLS NOT DISTINCT"""
    )
    op.execute("""CREATE TABLE event_type_duty_configurations (
	id UUID NOT NULL,
	district_id UUID NOT NULL,
	congregation_id UUID NOT NULL,
	duty_category_id UUID NOT NULL,
	event_categories VARCHAR(255)[] NOT NULL,
	enabled BOOLEAN NOT NULL,
	capacity INTEGER NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_duty_configuration_capacity CHECK (capacity > 0),
	FOREIGN KEY(district_id) REFERENCES districts (id) ON DELETE CASCADE,
	FOREIGN KEY(congregation_id) REFERENCES congregations (id) ON DELETE CASCADE,
	FOREIGN KEY(duty_category_id) REFERENCES event_duty_categories (id) ON DELETE CASCADE
)""")
    op.execute(
        """CREATE UNIQUE INDEX uq_duty_configuration_scope ON event_type_duty_configurations (congregation_id, duty_category_id)"""
    )
    op.execute("""CREATE TABLE duty_name_suggestions (
	id UUID NOT NULL,
	district_id UUID NOT NULL,
	congregation_id UUID,
	duty_category_id UUID NOT NULL,
	display_name VARCHAR(255) NOT NULL,
	normalized_name VARCHAR(255) NOT NULL,
	hidden BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(district_id) REFERENCES districts (id) ON DELETE CASCADE,
	FOREIGN KEY(congregation_id) REFERENCES congregations (id) ON DELETE CASCADE,
	FOREIGN KEY(duty_category_id) REFERENCES event_duty_categories (id) ON DELETE RESTRICT
)""")
    op.execute(
        """CREATE UNIQUE INDEX uq_duty_suggestion_identity ON duty_name_suggestions (district_id, congregation_id, duty_category_id, normalized_name) NULLS NOT DISTINCT"""
    )
    op.execute("""CREATE TABLE event_duty_assignments (
	id UUID NOT NULL,
	planning_slot_id UUID NOT NULL,
	duty_category_id UUID NOT NULL,
	district_id UUID NOT NULL,
	congregation_id UUID,
	display_name VARCHAR(255) NOT NULL,
	duty_label VARCHAR(255) NOT NULL,
	linked_user_sub VARCHAR(512),
	normalized_name VARCHAR(255),
	suggestion_id UUID,
	PRIMARY KEY (id),
	CONSTRAINT ck_duty_assignment_identity CHECK ((linked_user_sub IS NOT NULL AND normalized_name IS NULL) OR (linked_user_sub IS NULL AND normalized_name IS NOT NULL)),
	FOREIGN KEY(planning_slot_id) REFERENCES planning_slots (id) ON DELETE CASCADE,
	FOREIGN KEY(duty_category_id) REFERENCES event_duty_categories (id) ON DELETE RESTRICT,
	FOREIGN KEY(district_id) REFERENCES districts (id) ON DELETE CASCADE,
	FOREIGN KEY(congregation_id) REFERENCES congregations (id) ON DELETE RESTRICT,
	FOREIGN KEY(linked_user_sub) REFERENCES users (sub) ON DELETE RESTRICT,
	FOREIGN KEY(suggestion_id) REFERENCES duty_name_suggestions (id) ON DELETE SET NULL
)""")
    op.execute(
        """CREATE INDEX ix_duty_assignments_slot ON event_duty_assignments (planning_slot_id)"""
    )
    op.execute(
        """CREATE UNIQUE INDEX uq_duty_assignment_name ON event_duty_assignments (planning_slot_id, duty_category_id, normalized_name) WHERE linked_user_sub IS NULL"""
    )
    op.execute(
        """CREATE UNIQUE INDEX uq_duty_assignment_subject ON event_duty_assignments (planning_slot_id, duty_category_id, linked_user_sub) WHERE linked_user_sub IS NOT NULL"""
    )
    install_duty_policies(op)


def downgrade() -> None:
    remove_duty_policies(op)
    op.drop_table("event_duty_assignments")
    op.drop_table("duty_name_suggestions")
    op.drop_table("event_type_duty_configurations")
    op.drop_table("event_duty_categories")
    op.drop_constraint("ck_export_tokens_subject_internal", "export_tokens", type_="check")
    op.drop_constraint("fk_export_tokens_subject", "export_tokens", type_="foreignkey")
    op.drop_column("export_tokens", "subject_sub")
    op.drop_column("leaders", "service_end_date")
    op.drop_column("leaders", "hidden_from_lists")
