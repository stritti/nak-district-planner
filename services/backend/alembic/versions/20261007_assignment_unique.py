# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Allow only one service assignment per planning slot (#468).

The matrix shows one leader per slot, but nothing prevented a second
assignment row for the same slot; the matrix then picked one arbitrarily.

Steps (under a table lock, so no row can slip in between):

1. Backfill ``planning_slot_id`` from the legacy ``event_id`` where it still
   points at an existing planning slot, so legacy rows are covered too.
2. Resolve existing duplicates deterministically. Per planning slot the row
   kept is the "most confirmed" one, then the newest:
   status CONFIRMED > ASSIGNED > OPEN, then a linked leader (leader_id set)
   over a free-text name, then updated_at DESC, created_at DESC, id ASC.
   All other rows of that slot are copied to ``ARCHIVE_TABLE`` and then
   deleted, so nothing is lost: an operator can review them, and the
   downgrade restores them. The archive is owner-only (RLS forced without a
   policy, all privileges revoked), because it holds leader names.
3. Replace the plain index on ``planning_slot_id`` by a unique one.

service_assignments has no soft-delete column and every status (OPEN,
ASSIGNED, CONFIRMED) occupies the slot, so the index is not partial; rows
without planning_slot_id (unresolvable legacy rows) stay outside it because
NULLs are distinct.

Revision ID: 20261007_assignment_unique
Revises: 20261007_celery_tables
"""

from __future__ import annotations

import os

from alembic import op

revision = "20261007_assignment_unique"
down_revision = "20261007_celery_tables"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_service_assignments_planning_slot_id"

BACKFILL_PLANNING_SLOT_SQL = """
UPDATE service_assignments sa
SET planning_slot_id = sa.event_id
WHERE sa.planning_slot_id IS NULL
  AND EXISTS (SELECT 1 FROM planning_slots ps WHERE ps.id = sa.event_id);
"""

ARCHIVE_TABLE = "service_assignment_duplicates_468"

RANKED_DUPLICATES_SQL = """
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY planning_slot_id
               ORDER BY
                   CASE status
                       WHEN 'CONFIRMED' THEN 0
                       WHEN 'ASSIGNED' THEN 1
                       ELSE 2
                   END,
                   (leader_id IS NULL),
                   updated_at DESC,
                   created_at DESC,
                   id::text ASC
           ) AS rank
    FROM service_assignments
    WHERE planning_slot_id IS NOT NULL
"""

ARCHIVE_DUPLICATES_SQL = f"""
CREATE TABLE IF NOT EXISTS {ARCHIVE_TABLE} AS
SELECT sa.*, now() AS archived_at
FROM service_assignments sa
JOIN ({RANKED_DUPLICATES_SQL}) ranked ON ranked.id = sa.id
WHERE ranked.rank > 1;
"""

DELETE_DUPLICATES_SQL = f"""
DELETE FROM service_assignments sa
USING ({RANKED_DUPLICATES_SQL}) ranked
WHERE sa.id = ranked.id
  AND ranked.rank > 1;
"""

# No duplicates: no archive. Otherwise default privileges grant the app role
# access to the new table; take it away again, so the archived leader names
# are readable by the owner only.
LOCK_DOWN_ARCHIVE_SQL = f"""
DO $$
BEGIN
    IF to_regclass('{ARCHIVE_TABLE}') IS NULL THEN
        RETURN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM {ARCHIVE_TABLE}) THEN
        DROP TABLE {ARCHIVE_TABLE};
        RETURN;
    END IF;
    REVOKE ALL ON {ARCHIVE_TABLE} FROM PUBLIC;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :app_role) THEN
        EXECUTE format('REVOKE ALL ON {ARCHIVE_TABLE} FROM %I', :app_role);
    END IF;
    ALTER TABLE {ARCHIVE_TABLE} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {ARCHIVE_TABLE} FORCE ROW LEVEL SECURITY;
END
$$;
"""

# Downgrade: put the archived rows back (column list from the live table, so
# the archive's extra archived_at column is left out) and drop the archive.
RESTORE_DUPLICATES_SQL = f"""
DO $$
DECLARE
    cols text;
BEGIN
    IF to_regclass('{ARCHIVE_TABLE}') IS NULL THEN
        RETURN;
    END IF;
    SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position) INTO cols
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'service_assignments';
    EXECUTE format(
        'INSERT INTO service_assignments (%s) SELECT %s FROM {ARCHIVE_TABLE} ON CONFLICT (id) DO NOTHING',
        cols, cols
    );
    DROP TABLE {ARCHIVE_TABLE};
END
$$;
"""


def _app_role() -> str:
    return os.getenv("APP_DB_USER", "nak_app")


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    op.execute("LOCK TABLE service_assignments IN SHARE ROW EXCLUSIVE MODE")
    op.execute(BACKFILL_PLANNING_SLOT_SQL)
    op.execute(ARCHIVE_DUPLICATES_SQL)
    op.execute(LOCK_DOWN_ARCHIVE_SQL.replace(":app_role", _quote_literal(_app_role())))
    op.execute(DELETE_DUPLICATES_SQL)
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
    op.create_index(INDEX_NAME, "service_assignments", ["planning_slot_id"], unique=True)


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="service_assignments")
    op.create_index(INDEX_NAME, "service_assignments", ["planning_slot_id"])
    op.execute(RESTORE_DUPLICATES_SQL)
