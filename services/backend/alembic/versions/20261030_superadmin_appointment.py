# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Superadmins appoint further superadmins; the bootstrap grant runs once.

Revision 0017 reconciled ``users.is_superadmin`` with the configured
``SUPERADMIN_SUB`` on every login of that subject: it revoked every other
superadmin. That makes appointing further superadmins impossible. This
revision:

1. Adds ``app_superadmin_config.bootstrap_completed_at``. Installations whose
   configured subject is already a persisted superadmin are marked completed.
2. Replaces ``grant_bootstrap_superadmin``: while the bootstrap is pending and
   the authenticated subject is the configured one, it grants that subject and
   marks the bootstrap completed. Afterwards it never grants or revokes
   anything, so appointed superadmins survive and a revoked bootstrap subject
   stays revoked. It returns the persisted flag; the API reads the flag itself.
   The owner can re-arm a one-time grant (recovery, rotation) with
   ``UPDATE app_superadmin_config SET superadmin_sub = '<sub>',
   bootstrap_completed_at = NULL``; that revokes nobody.
3. Adds ``set_user_superadmin(target_sub, value)``, the only path for the
   application role to change the flag (it has no UPDATE privilege on the
   column). The caller, taken from the transaction's authenticated subject,
   must be a persisted superadmin. All superadmin rows and the target row are
   locked first, so concurrent revocations cannot remove the last superadmin.
   The function returns a status instead of raising, so the API can answer
   with 403/404/409 and audit the outcome in the same transaction.

Revision ID: 20261030_superadmin_appointment
Revises: 20261030_membership_scope_unique
"""

from __future__ import annotations

import os

from alembic import op

revision = "20261030_superadmin_appointment"
down_revision = "20261030_membership_scope_unique"
branch_labels = None
depends_on = None

BOOTSTRAP_SIGNATURE = "grant_bootstrap_superadmin(TEXT)"
SET_SIGNATURE = "set_user_superadmin(TEXT, BOOLEAN)"

MARK_EXISTING_BOOTSTRAP_SQL = """
UPDATE app_superadmin_config c
   SET bootstrap_completed_at = now(),
       updated_at = now()
 WHERE c.id = 1
   AND EXISTS (
       SELECT 1 FROM users u WHERE u.sub = c.superadmin_sub AND u.is_superadmin = true
   )
"""

BOOTSTRAP_ONCE_SQL = """
CREATE OR REPLACE FUNCTION grant_bootstrap_superadmin(
    p_user_sub TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_configured_sub TEXT;
    v_completed_at TIMESTAMPTZ;
BEGIN
    -- Fail closed when the authenticated-subject GUC is absent.
    IF p_user_sub IS NULL
       OR p_user_sub IS DISTINCT FROM current_setting('app.current_user_sub', true) THEN
        RAISE EXCEPTION 'user_sub does not match authenticated subject' USING ERRCODE = '42501';
    END IF;

    SELECT c.superadmin_sub, c.bootstrap_completed_at
      INTO v_configured_sub, v_completed_at
      FROM public.app_superadmin_config c
     WHERE c.id = 1;

    IF v_completed_at IS NULL AND p_user_sub = v_configured_sub THEN
        -- Re-read under a row lock, so two first logins grant only once.
        SELECT c.superadmin_sub, c.bootstrap_completed_at
          INTO v_configured_sub, v_completed_at
          FROM public.app_superadmin_config c
         WHERE c.id = 1
           FOR UPDATE;

        IF v_completed_at IS NULL AND p_user_sub = v_configured_sub THEN
            UPDATE public.users
               SET is_superadmin = true,
                   updated_at = now()
             WHERE sub = p_user_sub;

            IF FOUND THEN
                UPDATE public.app_superadmin_config
                   SET bootstrap_completed_at = now(),
                       updated_at = now()
                 WHERE id = 1;
            END IF;
        END IF;
    END IF;

    RETURN EXISTS (
        SELECT 1 FROM public.users
         WHERE sub = p_user_sub
           AND is_superadmin = true
    );
END;
$$
"""

SET_SUPERADMIN_SQL = """
CREATE OR REPLACE FUNCTION set_user_superadmin(
    p_target_sub TEXT,
    p_value BOOLEAN
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_actor TEXT := NULLIF(current_setting('app.current_user_sub', true), '');
    v_current BOOLEAN;
BEGIN
    IF v_actor IS NULL OR p_target_sub IS NULL OR p_value IS NULL THEN
        RAISE EXCEPTION 'authenticated subject and target required' USING ERRCODE = '42501';
    END IF;

    -- Serialize every change of the flag: whoever comes second sees the
    -- committed state of the first, so the last superadmin always remains.
    PERFORM 1
       FROM public.users
      WHERE is_superadmin = true OR sub = p_target_sub
      ORDER BY sub
        FOR UPDATE;

    IF NOT EXISTS (
        SELECT 1 FROM public.users WHERE sub = v_actor AND is_superadmin = true
    ) THEN
        RETURN 'forbidden';
    END IF;

    SELECT is_superadmin INTO v_current FROM public.users WHERE sub = p_target_sub;
    IF NOT FOUND THEN
        RETURN 'not_found';
    END IF;
    IF v_current = p_value THEN
        RETURN 'unchanged';
    END IF;
    IF NOT p_value AND NOT EXISTS (
        SELECT 1 FROM public.users WHERE is_superadmin = true AND sub <> p_target_sub
    ) THEN
        RETURN 'last_superadmin';
    END IF;

    UPDATE public.users
       SET is_superadmin = p_value,
           updated_at = now()
     WHERE sub = p_target_sub;

    RETURN CASE WHEN p_value THEN 'granted' ELSE 'revoked' END;
END;
$$
"""

# Revision 0017's function, restored by the downgrade.
BOOTSTRAP_RECONCILE_SQL = """
CREATE OR REPLACE FUNCTION grant_bootstrap_superadmin(
    p_user_sub TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_configured_sub TEXT;
BEGIN
    IF p_user_sub IS NULL
       OR p_user_sub IS DISTINCT FROM current_setting('app.current_user_sub', true) THEN
        RAISE EXCEPTION 'user_sub does not match authenticated subject' USING ERRCODE = '42501';
    END IF;

    SELECT c.superadmin_sub
      INTO v_configured_sub
      FROM public.app_superadmin_config c
     WHERE c.id = 1;

    IF v_configured_sub IS NOT NULL THEN
        IF p_user_sub <> v_configured_sub THEN
            RETURN false;
        END IF;

        UPDATE public.users
           SET is_superadmin = false,
               updated_at = now()
         WHERE is_superadmin = true
           AND sub <> v_configured_sub;

        UPDATE public.users
           SET is_superadmin = true,
           updated_at = now()
         WHERE sub = v_configured_sub
           AND is_superadmin = false;

        RETURN true;
    END IF;

    RETURN EXISTS (
        SELECT 1 FROM public.users
         WHERE sub = p_user_sub
           AND is_superadmin = true
    );
END;
$$
"""


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _grant_execute(signature: str) -> None:
    app_role = os.getenv("APP_DB_USER", "nak_app")
    op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {_quote_literal(app_role)}) THEN
                GRANT EXECUTE ON FUNCTION {signature} TO {_quote_ident(app_role)};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    op.execute("ALTER TABLE app_superadmin_config ADD COLUMN bootstrap_completed_at TIMESTAMPTZ")
    op.execute(MARK_EXISTING_BOOTSTRAP_SQL)
    op.execute(BOOTSTRAP_ONCE_SQL)
    _grant_execute(BOOTSTRAP_SIGNATURE)
    op.execute(SET_SUPERADMIN_SQL)
    _grant_execute(SET_SIGNATURE)


def downgrade() -> None:
    op.execute(f"DROP FUNCTION IF EXISTS {SET_SIGNATURE}")
    op.execute(BOOTSTRAP_RECONCILE_SQL)
    _grant_execute(BOOTSTRAP_SIGNATURE)
    op.execute("ALTER TABLE app_superadmin_config DROP COLUMN IF EXISTS bootstrap_completed_at")
