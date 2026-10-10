# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Create the Celery broker and result tables as the database owner.

Celery uses PostgreSQL as broker (kombu SQLAlchemy transport) and result
backend. Both create their tables lazily on first use, which needs CREATE on
schema public. Worker and beat run as the runtime role, which has no DDL
rights, so on a fresh database they crashed with "permission denied for schema
public". The DDL below matches what kombu/celery would create; IF NOT EXISTS
keeps installations where an owner-run process already created them working.

Revision ID: 20261007_celery_tables
Revises: 20261001_slot_gaps
"""

from __future__ import annotations

import os

from alembic import op

revision = "20261007_celery_tables"
down_revision = "20261001_slot_gaps"
branch_labels = None
depends_on = None

TABLES = ("kombu_queue", "kombu_message", "celery_taskmeta", "celery_tasksetmeta")
SEQUENCES = ("queue_id_sequence", "message_id_sequence", "task_id_sequence", "taskset_id_sequence")


def upgrade() -> None:
    for sequence in SEQUENCES:
        op.execute(f"CREATE SEQUENCE IF NOT EXISTS {sequence}")
    statements = """
        CREATE TABLE IF NOT EXISTS kombu_queue (
            id integer PRIMARY KEY,
            name varchar(200) UNIQUE
        );
        CREATE TABLE IF NOT EXISTS kombu_message (
            id integer PRIMARY KEY,
            visible boolean,
            "timestamp" timestamp without time zone,
            payload text NOT NULL,
            version smallint NOT NULL,
            queue_id integer CONSTRAINT "FK_kombu_message_queue" REFERENCES kombu_queue (id)
        );
        CREATE INDEX IF NOT EXISTS ix_kombu_message_visible ON kombu_message (visible);
        CREATE INDEX IF NOT EXISTS ix_kombu_message_timestamp ON kombu_message ("timestamp");
        CREATE INDEX IF NOT EXISTS ix_kombu_message_timestamp_id
            ON kombu_message ("timestamp", id);
        CREATE TABLE IF NOT EXISTS celery_taskmeta (
            id integer PRIMARY KEY,
            task_id varchar(155) UNIQUE,
            status varchar(50),
            result bytea,
            date_done timestamp without time zone,
            traceback text,
            name varchar(155),
            args bytea,
            kwargs bytea,
            worker varchar(155),
            retries integer,
            queue varchar(155)
        );
        CREATE INDEX IF NOT EXISTS ix_celery_taskmeta_date_done ON celery_taskmeta (date_done);
        CREATE TABLE IF NOT EXISTS celery_tasksetmeta (
            id integer PRIMARY KEY,
            taskset_id varchar(155) UNIQUE,
            result bytea,
            date_done timestamp without time zone
        );
        CREATE INDEX IF NOT EXISTS ix_celery_tasksetmeta_date_done
            ON celery_tasksetmeta (date_done)
    """
    for statement in statements.split(";"):
        op.execute(statement)
    app_role = '"' + os.getenv("APP_DB_USER", "nak_app").replace('"', '""') + '"'
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {', '.join(TABLES)} TO {app_role}")
    op.execute(f"GRANT USAGE ON SEQUENCE {', '.join(SEQUENCES)} TO {app_role}")


def downgrade() -> None:
    """Keep the tables: they may predate this revision and hold queued tasks."""
