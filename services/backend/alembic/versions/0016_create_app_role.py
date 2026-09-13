"""create application database role without BYPASSRLS

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-12 00:00:00.000000

"""

from __future__ import annotations

import os
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _app_role() -> str:
    return os.getenv("APP_DB_USER", "nak_app")


def upgrade() -> None:
    """Create application role without BYPASSRLS and grant necessary permissions."""
    app_role = _app_role()
    app_role_ident = _quote_ident(app_role)
    app_password = os.getenv("APP_DB_PASSWORD")
    password_clause = f" PASSWORD {_quote_literal(app_password)}" if app_password else ""
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = {_quote_literal(app_role)}) THEN
                CREATE ROLE {app_role_ident} WITH LOGIN NOBYPASSRLS{password_clause};
            ELSE
                ALTER ROLE {app_role_ident} WITH LOGIN NOBYPASSRLS{password_clause};
            END IF;
        END $$;
        """
    )

    # Grant usage on schema
    op.execute(f"GRANT USAGE ON SCHEMA public TO {app_role_ident};")

    # Grant all privileges on all tables in public schema
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {app_role_ident};")
    op.execute(f"REVOKE INSERT, UPDATE ON users FROM {app_role_ident};")
    op.execute(
        f"GRANT INSERT (id, sub, email, username, name, given_name, family_name, created_at, updated_at), "
        f"UPDATE (email, username, name, given_name, family_name, updated_at) ON users TO {app_role_ident};"
    )

    # Grant usage on all sequences
    op.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {app_role_ident};")

    # Grant execute on all functions
    op.execute(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {app_role_ident};")

    # Set default privileges for future objects
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_role_ident};"
    )
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO {app_role_ident};")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO {app_role_ident};")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION can_admin_membership(p_scope_type TEXT, p_scope_id UUID)
        RETURNS BOOLEAN
        LANGUAGE sql
        SECURITY DEFINER
        STABLE
        SET search_path = public
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM memberships m
                WHERE m.user_sub = current_setting('app.current_user_sub', true)
                  AND m.role IN ('CONGREGATION_ADMIN', 'DISTRICT_ADMIN')
                  AND (
                    (p_scope_type = 'DISTRICT' AND m.scope_type = 'DISTRICT' AND m.scope_id = p_scope_id)
                    OR (p_scope_type = 'CONGREGATION' AND (
                        (m.scope_type = 'CONGREGATION' AND m.scope_id = p_scope_id)
                        OR (m.scope_type = 'DISTRICT' AND EXISTS (
                            SELECT 1 FROM congregations c
                            WHERE c.id = p_scope_id AND c.district_id = m.scope_id
                        ))
                    ))
                  )
            )
        $$;
        """
    )
    op.execute("REVOKE ALL ON FUNCTION can_admin_membership(TEXT, UUID) FROM PUBLIC;")
    op.execute(f"GRANT EXECUTE ON FUNCTION can_admin_membership(TEXT, UUID) TO {app_role_ident};")
    op.execute(f"GRANT EXECUTE ON FUNCTION link_approved_registration(TEXT, TEXT) TO {app_role_ident};")

    # Grant the role to the current user (for administration)
    # Note: In production, the application should connect as nak_app, not as the superuser
    op.execute(f"GRANT {app_role_ident} TO CURRENT_USER;")


def downgrade() -> None:
    """Drop application role and revoke permissions."""
    app_role = _app_role()
    app_role_ident = _quote_ident(app_role)
    # Revoke default privileges
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {app_role_ident};")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM {app_role_ident};")
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM {app_role_ident};")

    # Revoke privileges
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {app_role_ident};")
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {app_role_ident};")
    op.execute(f"REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM {app_role_ident};")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {app_role_ident};")

    # Drop the role
    op.execute(f"DROP ROLE IF EXISTS {app_role_ident};")
