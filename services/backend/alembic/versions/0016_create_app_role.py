"""create application database role without BYPASSRLS

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-12 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create application role without BYPASSRLS and grant necessary permissions."""
    # Create the application role without BYPASSRLS (cannot bypass RLS)
    op.execute("CREATE ROLE nak_app WITH LOGIN NOBYPASSRLS;")

    # Grant usage on schema
    op.execute("GRANT USAGE ON SCHEMA public TO nak_app;")

    # Grant all privileges on all tables in public schema
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nak_app;")

    # Grant usage on all sequences
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO nak_app;")

    # Grant execute on all functions
    op.execute("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO nak_app;")

    # Set default privileges for future objects
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nak_app;"
    )
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO nak_app;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO nak_app;")

    # Grant the role to the current user (for administration)
    # Note: In production, the application should connect as nak_app, not as the superuser
    op.execute("GRANT nak_app TO CURRENT_USER;")


def downgrade() -> None:
    """Drop application role and revoke permissions."""
    # Revoke default privileges
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM nak_app;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM nak_app;")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM nak_app;")

    # Revoke privileges
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM nak_app;")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM nak_app;")
    op.execute("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM nak_app;")
    op.execute("REVOKE USAGE ON SCHEMA public FROM nak_app;")

    # Drop the role
    op.execute("DROP ROLE IF EXISTS nak_app;")
