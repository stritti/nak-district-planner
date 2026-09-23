"""add owner-controlled bootstrap superadmin state

Revision ID: 0017
Revises: 1a2b3c4d5e6f
Create Date: 2026-09-23 00:00:00.000000
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from alembic import op
from app.config import settings

# revision identifiers, used by Alembic.
revision: str = "0017"
down_revision: str | None = "1a2b3c4d5e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNCTION_SIGNATURE = "grant_bootstrap_superadmin(TEXT)"


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    """Create owner-controlled superadmin configuration and bounded grant helper.

    The application role cannot write ``users.is_superadmin`` (see revision
    0016), so a fresh installation has no path to bootstrap the initial
    superadmin. This revision stores the deployment's configured superadmin
    subject (``SUPERADMIN_SUB``, seeded once when the migration runs) in
    ``app_superadmin_config`` — a table writable only by the database owner —
    and exposes a bounded SECURITY DEFINER function that derives all
    authorization facts from that owner-controlled state:

    - With a configured subject, only that exact subject is granted the flag
      (OIDC subjects are opaque case-sensitive identifiers, compared exactly)
      and every previously persisted flag for another subject is revoked, so
      rotations enforce that exactly the configured subject is superadmin.
    - Without a configured subject, the migration pins the earliest
      registered account (deterministic original first user) as the fallback
      subject on existing installations, preserving the documented guarantee
      for upgrades where all users may carry is_superadmin = false. When the
      migration runs on a still empty installation, the fallback remains
      open for the first login, serialized with a transaction-scoped advisory
      lock taken before any caller-side row insert and re-checked against
      existing superadmins so concurrent first logins cannot both become
      superadmin. Because every non-empty installation has a pinned subject,
      no account created after the seed can become superadmin just by logging
      in first.

    The function takes only the caller's subject (bound to the session's
    authenticated subject GUC) and never trusts caller-supplied authorization
    facts: an application-role session cannot forge eligibility because the
    configuration table is not writable or readable by the application role.
    """
    op.execute(
        """
        CREATE TABLE app_superadmin_config (
            id SMALLINT PRIMARY KEY CHECK (id = 1),
            superadmin_sub TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    configured_sub = settings.superadmin_sub
    configured_literal = (
        _quote_literal(configured_sub) if configured_sub is not None else "NULL"
    )
    # Without a configured subject, the first-ever registered user keeps the
    # documented bootstrap guarantee. On an upgrade of an existing
    # installation all users may carry is_superadmin = false, so the fallback
    # subject is pinned deterministically during migration (an existing
    # superadmin, else the earliest created account) instead of whichever
    # account happens to log in first after the upgrade.
    op.execute(
        f"""
        INSERT INTO app_superadmin_config (id, superadmin_sub)
        SELECT 1,
               COALESCE(
                   {configured_literal},
                   (SELECT u.sub FROM users u WHERE u.is_superadmin = true
                     ORDER BY u.created_at, u.id LIMIT 1),
                   (SELECT u.sub FROM users u ORDER BY u.created_at, u.id LIMIT 1)
               )
        """
    )

    app_role = os.getenv("APP_DB_USER", "nak_app")
    # The configuration is owner-controlled state: the application role must
    # not read or modify it (default privileges from revision 0016 would
    # otherwise grant full access to newly created tables).
    op.execute(f"REVOKE ALL ON app_superadmin_config FROM {_quote_ident(app_role)}")
    op.execute("REVOKE ALL ON app_superadmin_config FROM PUBLIC")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION grant_bootstrap_superadmin(
            p_user_sub TEXT
        )
        RETURNS BOOLEAN
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        DECLARE
            v_configured_sub TEXT;
            v_granted BOOLEAN;
        BEGIN
            IF p_user_sub IS NULL OR p_user_sub <> current_setting('app.current_user_sub', true) THEN
                RAISE EXCEPTION 'user_sub does not match authenticated subject' USING ERRCODE = '42501';
            END IF;

            SELECT c.superadmin_sub
              INTO v_configured_sub
              FROM app_superadmin_config c
             WHERE c.id = 1;

            IF v_configured_sub IS NOT NULL THEN
                IF p_user_sub <> v_configured_sub THEN
                    RETURN false;
                END IF;

                -- Reconcile persisted grants with the owner-controlled
                -- configuration so exactly the configured subject keeps the
                -- flag, including after rotations of SUPERADMIN_SUB.
                UPDATE users
                   SET is_superadmin = false,
                       updated_at = now()
                 WHERE is_superadmin = true
                   AND sub <> v_configured_sub;

                UPDATE users
                   SET is_superadmin = true,
                   updated_at = now()
                 WHERE sub = v_configured_sub
                   AND is_superadmin = false;

                RETURN true;
            END IF;

            -- No configured subject and no pinned fallback: the installation
            -- had no users when the configuration was seeded, so the seed
            -- pinned nothing and the first login receives the bootstrap grant.
            -- A non-empty installation always has a pinned subject, so no
            -- account created after the seed can become superadmin just by
            -- logging in first. Once a bootstrap superadmin exists, report
            -- whether the caller is that persisted superadmin instead of
            -- returning false unconditionally: the already-bootstrapped first
            -- user must keep the flag on subsequent requests.
            PERFORM pg_advisory_xact_lock(hashtext('nak:grant_bootstrap_superadmin'));
            IF EXISTS (SELECT 1 FROM users WHERE is_superadmin = true) THEN
                RETURN EXISTS (
                    SELECT 1 FROM users
                     WHERE sub = p_user_sub
                       AND is_superadmin = true
                );
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
    """Drop bootstrap superadmin helper and owner-controlled configuration."""
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
    op.execute("DROP TABLE IF EXISTS app_superadmin_config")
