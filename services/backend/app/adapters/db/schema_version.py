# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Fail-fast verification that the runtime database matches the Alembic head."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine


class SchemaVersionError(RuntimeError):
    """Raised when the database schema is unavailable or not at the expected head."""


def expected_schema_revisions(config_path: Path | str = "alembic.ini") -> set[str]:
    """Return the revision set that the checked-out application expects."""
    config = Config(str(config_path))
    heads = set(ScriptDirectory.from_config(config).get_heads())
    if not heads:
        raise SchemaVersionError("Alembic has no configured head revision")
    return heads


async def assert_database_schema_current(
    engine: AsyncEngine,
    *,
    config_path: Path | str = "alembic.ini",
) -> None:
    """Fail when ``alembic_version`` does not match the checked-out migration head.

    This deliberately performs no migration. Applying DDL remains a deployment
    responsibility of the one-shot ``migrate`` service.
    """
    expected = expected_schema_revisions(config_path)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT version_num FROM alembic_version"))
            actual = {str(row[0]) for row in result}
    # OSError covers driver-level connection failures (refused, DNS, timeout)
    # that asyncpg raises without a SQLAlchemy wrapper.
    except (SQLAlchemyError, OSError) as exc:
        raise SchemaVersionError(
            "Could not read database schema version from alembic_version"
        ) from exc

    if actual != expected:
        raise SchemaVersionError(
            "Database schema revision mismatch: "
            f"expected {sorted(expected)!r}, got {sorted(actual)!r}. "
            "Run the deployment migration before starting the runtime service."
        )
