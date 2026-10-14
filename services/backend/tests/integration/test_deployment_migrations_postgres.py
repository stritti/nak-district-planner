# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Deployment migration gates against a real, migrated PostgreSQL database.

Uses the same configuration as ``test_rls_postgres.py``:
``RLS_TEST_DATABASE_URL`` (owner DSN) and ``RLS_TEST_APP_PASSWORD``.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")
from psycopg2.extensions import make_dsn, parse_dsn  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.adapters.db.schema_version import assert_database_schema_current  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parents[2]
OWNER_DSN = os.getenv("RLS_TEST_DATABASE_URL")
APP_PASSWORD = os.getenv("RLS_TEST_APP_PASSWORD")
APP_ROLE = os.getenv("APP_DB_USER", "nak_app")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not (OWNER_DSN and APP_PASSWORD),
        reason="RLS_TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
    ),
]


def _asyncpg_url(user: str, password: str) -> str:
    p = parse_dsn(OWNER_DSN)
    return (
        f"postgresql+asyncpg://{user}:{password}@{p.get('host', 'localhost')}:"
        f"{p.get('port', '5432')}/{p['dbname']}"
    )


def test_runtime_role_passes_schema_guard_on_migrated_database() -> None:
    async def check() -> None:
        engine = create_async_engine(_asyncpg_url(APP_ROLE, APP_PASSWORD), poolclass=NullPool)
        try:
            await assert_database_schema_current(engine, config_path=BACKEND_ROOT / "alembic.ini")
        finally:
            await engine.dispose()

    asyncio.run(check())


def test_concurrent_migration_waits_for_advisory_lock() -> None:
    lock_key = 0x6E616B6D696772
    env_py = (BACKEND_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    assert f"MIGRATION_LOCK_KEY = 0x{lock_key:X}" in env_py

    owner = parse_dsn(OWNER_DSN)
    holder = psycopg2.connect(make_dsn(OWNER_DSN))
    holder.autocommit = True
    env = {
        **os.environ,
        "DATABASE_URL": _asyncpg_url(owner["user"], owner.get("password", "")),
        "MIGRATION_DATABASE_URL": "",
    }
    try:
        holder.cursor().execute("SELECT pg_advisory_lock(%s)", (lock_key,))
        proc = subprocess.Popen(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)
        assert proc.poll() is None, "migration must block while another run holds the lock"
    finally:
        holder.cursor().execute("SELECT pg_advisory_unlock(%s)", (lock_key,))
        holder.close()
    assert proc.wait(timeout=60) == 0


def test_runtime_role_can_use_celery_broker_tables_without_ddl() -> None:
    owner = parse_dsn(OWNER_DSN)
    app = psycopg2.connect(make_dsn(OWNER_DSN, user=APP_ROLE, password=APP_PASSWORD))
    try:
        with app.cursor() as cur:
            cur.execute("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
            assert cur.fetchone()[0] is False, "runtime role must not have DDL rights"
            cur.execute(
                "INSERT INTO kombu_queue (id, name) VALUES (nextval('queue_id_sequence'), %s)",
                (f"probe-{owner['dbname']}-{time.time_ns()}",),
            )
            cur.execute(
                "INSERT INTO celery_taskmeta (id, task_id, status) "
                "VALUES (nextval('task_id_sequence'), %s, 'PENDING')",
                (f"probe-{time.time_ns()}",),
            )
        app.rollback()
    finally:
        app.close()
