"""add security-definer registration auto-link function

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-11 00:00:00.000000

"""

from __future__ import annotations

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FUNCTION_SIGNATURE = "link_approved_registration(TEXT, TEXT)"


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    """Create bounded registration auto-link helper for post-login membership grants."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION link_approved_registration(
            p_user_sub TEXT,
            p_email TEXT
        )
        RETURNS TABLE(candidate_count INTEGER, granted_role TEXT, granted_scope_type TEXT, granted_scope_id UUID)
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            v_registration_id UUID;
            v_registration_ids UUID[];
            v_assigned_role TEXT;
            v_assigned_scope_type TEXT;
            v_assigned_scope_id UUID;
            v_now TIMESTAMPTZ;
        BEGIN
            IF p_user_sub IS NULL OR p_user_sub <> current_setting('app.current_user_sub', true) THEN
                RAISE EXCEPTION 'user_sub does not match authenticated subject' USING ERRCODE = '42501';
            END IF;

            SELECT count(*)::INTEGER, array_agg(candidate.id)
              INTO candidate_count, v_registration_ids
              FROM (
                  SELECT lr.id
                    FROM leader_registrations lr
                   WHERE lr.status = 'APPROVED'
                     AND lr.user_sub IS NULL
                     AND lower(lr.email) = lower(trim(p_email))
                   FOR UPDATE
              ) AS candidate;

            IF candidate_count <> 1 THEN
                granted_role := NULL;
                granted_scope_type := NULL;
                granted_scope_id := NULL;
                RETURN NEXT;
                RETURN;
            END IF;

            v_registration_id := v_registration_ids[1];

            SELECT lr.assigned_role, lr.assigned_scope_type, lr.assigned_scope_id
              INTO v_assigned_role, v_assigned_scope_type, v_assigned_scope_id
              FROM leader_registrations lr
             WHERE lr.id = v_registration_id;

            IF v_assigned_role IS NULL OR v_assigned_scope_type IS NULL OR v_assigned_scope_id IS NULL THEN
                granted_role := NULL;
                granted_scope_type := NULL;
                granted_scope_id := NULL;
                RETURN NEXT;
                RETURN;
            END IF;

            v_now := now();

            UPDATE leader_registrations
               SET user_sub = p_user_sub,
                   updated_at = v_now
             WHERE id = v_registration_id;

            UPDATE memberships
               SET role = v_assigned_role,
                   updated_at = v_now
             WHERE user_sub = p_user_sub
               AND scope_type = v_assigned_scope_type
               AND scope_id = v_assigned_scope_id;

            IF NOT FOUND THEN
                INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, updated_at)
                VALUES (
                    gen_random_uuid(),
                    p_user_sub,
                    v_assigned_role,
                    v_assigned_scope_type,
                    v_assigned_scope_id,
                    v_now,
                    v_now
                );
            END IF;

            granted_role := v_assigned_role;
            granted_scope_type := v_assigned_scope_type;
            granted_scope_id := v_assigned_scope_id;
            RETURN NEXT;
        END;
        $$;
        """
    )
    app_role = os.getenv("APP_DB_USER", "nak_app")
    op.execute(f"REVOKE ALL ON FUNCTION {FUNCTION_SIGNATURE} FROM PUBLIC")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {_quote_literal(app_role)}) THEN
                GRANT EXECUTE ON FUNCTION {FUNCTION_SIGNATURE} TO {_quote_ident(app_role)};
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    """Drop registration auto-link helper."""
    app_role = os.getenv("APP_DB_USER", "nak_app")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {_quote_literal(app_role)}) THEN
                REVOKE ALL ON FUNCTION {FUNCTION_SIGNATURE} FROM {_quote_ident(app_role)};
            END IF;
        END $$;
        """
    )
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION_SIGNATURE}")
