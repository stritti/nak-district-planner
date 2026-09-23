"""add security-definer bootstrap superadmin function

Revision ID: 0017
Revises: 1a2b3c4d5e6f
Create Date: 2026-09-23 00:00:00.000000
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: str | None = "1a2b3c4d5e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNCTION_SIGNATURE = "grant_bootstrap_superadmin(TEXT, TEXT, BOOLEAN)"


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    """Create bounded helper to persist the bootstrap superadmin flag.

    The application role cannot write ``users.is_superadmin`` (see revision
    0016), so a fresh installation has no path to bootstrap the initial
    superadmin. This SECURITY DEFINER function exposes a bounded grant: it
    binds the target subject to the session's authenticated subject GUC and
    only persists the flag for the subject configured via ``SUPERADMIN_SUB``
    (owner-controlled deployment configuration, compared exactly because OIDC
    subjects are opaque case-sensitive identifiers) or for the very first user
    of an empty installation when no subject is configured. The first-user
    grant is serialized with a transaction-scoped advisory lock taken before
    any caller-side row insert and re-checked against existing superadmins so
    concurrent first logins cannot both become superadmin and cannot deadlock
    with their own users-row locks.
    """
    op.execute(
        """
        CREATE OR REPLACE FUNCTION grant_bootstrap_superadmin(
            p_user_sub TEXT,
            p_configured_sub TEXT,
            p_is_first_login BOOLEAN
        )
        RETURNS BOOLEAN
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            v_granted BOOLEAN;
        BEGIN
            IF p_user_sub IS NULL OR p_user_sub <> current_setting('app.current_user_sub', true) THEN
                RAISE EXCEPTION 'user_sub does not match authenticated subject' USING ERRCODE = '42501';
            END IF;

            IF COALESCE(p_is_first_login, false) AND p_configured_sub IS NULL THEN
                PERFORM pg_advisory_xact_lock(hashtext('nak:grant_bootstrap_superadmin'));
                IF EXISTS (SELECT 1 FROM users WHERE is_superadmin = true) THEN
                    RETURN false;
                END IF;
            ELSIF p_configured_sub IS NULL OR p_configured_sub <> p_user_sub THEN
                RETURN false;
            END IF;

            UPDATE users
               SET is_superadmin = true,
                   updated_at = now()
             WHERE sub = p_user_sub
               AND is_superadmin = false
            RETURNING true
            INTO v_granted;

            RETURN COALESCE(v_granted, false);
        END;
        $$
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
    """Drop bootstrap superadmin helper."""
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
