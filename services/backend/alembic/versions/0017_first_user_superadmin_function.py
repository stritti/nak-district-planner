"""add narrow first-user superadmin bootstrap function

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-13 00:00:00.000000

"""

from __future__ import annotations

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _app_role() -> str:
    return os.getenv("APP_DB_USER", "nak_app")


def upgrade() -> None:
    app_role_ident = _quote_ident(_app_role())
    op.execute("DROP FUNCTION IF EXISTS grant_superadmin_bootstrap(TEXT);")
    op.execute("DROP FUNCTION IF EXISTS grant_first_user_superadmin(TEXT);")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS superadmin_bootstrap_subjects (
            subject TEXT PRIMARY KEY,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
        """
    )
    superadmin_sub = os.getenv("SUPERADMIN_SUB")
    if superadmin_sub:
        op.execute(
            "INSERT INTO superadmin_bootstrap_subjects (subject) VALUES "
            f"({_quote_literal(superadmin_sub)}) ON CONFLICT (subject) DO NOTHING;"
        )
    op.execute("REVOKE ALL ON superadmin_bootstrap_subjects FROM PUBLIC;")
    op.execute(f"REVOKE ALL ON superadmin_bootstrap_subjects FROM {app_role_ident};")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION grant_trusted_superadmin_bootstrap(p_user_sub TEXT)
        RETURNS BOOLEAN
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            promoted_count INTEGER := 0;
        BEGIN
            LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE;
            LOCK TABLE superadmin_bootstrap_subjects IN SHARE MODE;

            UPDATE users
            SET is_superadmin = true,
                updated_at = NOW()
            WHERE sub = p_user_sub
              AND (
                  (
                      (SELECT COUNT(*) FROM users) = 1
                      AND NOT EXISTS (
                          SELECT 1 FROM users u
                          WHERE u.sub <> p_user_sub OR u.is_superadmin = true
                      )
                  )
                  OR EXISTS (
                      SELECT 1
                      FROM superadmin_bootstrap_subjects sbs
                      WHERE sbs.subject = p_user_sub
                  )
              );

            GET DIAGNOSTICS promoted_count = ROW_COUNT;
            RETURN promoted_count = 1;
        END;
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION grant_trusted_superadmin_bootstrap(TEXT) FROM PUBLIC;")
    op.execute(f"GRANT EXECUTE ON FUNCTION grant_trusted_superadmin_bootstrap(TEXT) TO {app_role_ident};")
    op.execute("DROP POLICY IF EXISTS leaders_tenant_isolation_policy ON leaders;")
    op.execute(
        """
        /* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
        CREATE POLICY leaders_tenant_isolation_policy ON leaders
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1
                    FROM users
                    WHERE sub = current_setting('app.current_user_sub', true)
                      AND is_superadmin = true
                )
                OR current_setting('app.is_system_worker', true) = 'true'
                OR EXISTS (
                    SELECT 1
                    FROM memberships m
                    WHERE m.user_sub = current_setting('app.current_user_sub', true)
                      AND m.scope_type = 'DISTRICT'
                      AND m.scope_id = leaders.district_id
                )
                OR (
                    leaders.congregation_id IS NOT NULL
                    AND EXISTS (
                        SELECT 1
                        FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub', true)
                          AND m.scope_type = 'CONGREGATION'
                          AND m.scope_id = leaders.congregation_id
                    )
                )
                OR leaders.user_sub = current_setting('app.current_user_sub', true)
                OR EXISTS (
                    SELECT 1
                    FROM service_assignments sa
                    JOIN planning_slots ps ON ps.id = sa.planning_slot_id
                    JOIN export_tokens et ON et.token = current_setting('app.current_export_token', true)
                    WHERE sa.leader_id = leaders.id
                      AND et.token_type = 'INTERNAL'
                      AND et.district_id = ps.district_id
                      AND (et.congregation_id IS NULL OR et.congregation_id = ps.congregation_id)
                )
            );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS leaders_tenant_isolation_policy ON leaders;")
    op.execute(
        """
        /* # nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs */
        CREATE POLICY leaders_tenant_isolation_policy ON leaders
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1
                    FROM users
                    WHERE sub = current_setting('app.current_user_sub', true)
                      AND is_superadmin = true
                )
                OR current_setting('app.is_system_worker', true) = 'true'
                OR EXISTS (
                    SELECT 1
                    FROM memberships m
                    WHERE m.user_sub = current_setting('app.current_user_sub', true)
                      AND m.scope_type = 'DISTRICT'
                      AND m.scope_id = leaders.district_id
                )
                OR (
                    leaders.congregation_id IS NOT NULL
                    AND EXISTS (
                        SELECT 1
                        FROM memberships m
                        WHERE m.user_sub = current_setting('app.current_user_sub', true)
                          AND m.scope_type = 'CONGREGATION'
                          AND m.scope_id = leaders.congregation_id
                    )
                )
                OR leaders.user_sub = current_setting('app.current_user_sub', true)
            );
        """
    )
    op.execute("DROP FUNCTION IF EXISTS grant_trusted_superadmin_bootstrap(TEXT);")
    op.execute("DROP TABLE IF EXISTS superadmin_bootstrap_subjects;")
