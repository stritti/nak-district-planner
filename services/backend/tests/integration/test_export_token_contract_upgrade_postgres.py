# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""End-to-end upgrade of the irreversible export-token contract migration (#602).

Each test creates a throwaway database, migrates it to the immediate
predecessor revision, seeds *existing* plaintext tokens as an old installation
would have them, upgrades to the contract revision for real and inspects the result.

TEST_DATABASE_URL must be a PostgreSQL superuser URL
(``postgresql+asyncpg://...``); databases are created and dropped on its server.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")
from sqlalchemy import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.adapters.db.repositories.export_token import SqlExportTokenRepository  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PREDECESSOR = "20261016_notif_user_state"
CONTRACT = "20261016_contract_export_tokens"

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture
def database():
    base = make_url(os.environ["TEST_DATABASE_URL"])
    name = f"contract_{uuid.uuid4().hex[:10]}"
    admin = psycopg2.connect(
        host=base.host, port=base.port, user=base.username, password=base.password,
        dbname=base.database,
    )
    admin.autocommit = True
    admin.cursor().execute(f'CREATE DATABASE "{name}"')
    url = base.set(database=name)
    yield url
    admin.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    admin.close()


def _alembic(url, target: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "DATABASE_URL": url.render_as_string(hide_password=False),
        "MIGRATION_DATABASE_URL": "",
    }
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=BACKEND_ROOT, env=env, capture_output=True, text=True, check=False,
    )


def _connect(url):
    conn = psycopg2.connect(
        host=url.host, port=url.port, user=url.username, password=url.password, dbname=url.database
    )
    conn.autocommit = True
    return conn


def _seed(conn, rows: list[tuple[str, str, str | None]]):
    """rows: (kind, plaintext token, stored hash or None); kind PERSONAL = subject-bound feed."""
    cur = conn.cursor()
    district = uuid.uuid4()
    cur.execute(
        "INSERT INTO districts (id, name, created_at, updated_at) VALUES (%s, 'B', now(), now())",
        (str(district),),
    )
    ids = []
    for kind, token, token_hash in rows:
        token_id = uuid.uuid4()
        ids.append(token_id)
        subject = None
        if kind == "PERSONAL":
            subject = f"sub-{uuid.uuid4().hex[:8]}"
            cur.execute(
                "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, false, now(), now())",
                (str(uuid.uuid4()), subject, f"{subject}@example.test", subject),
            )
        cur.execute(
            "INSERT INTO export_tokens (id, token, token_hash, label, token_type, district_id, "
            "subject_sub, created_at) VALUES (%s, %s, %s, 'legacy', %s, %s, %s, now())",
            (
                str(token_id), token, token_hash,
                "INTERNAL" if kind == "PERSONAL" else kind, str(district), subject,
            ),
        )
    return ids


def _columns(conn) -> set[str]:
    cur = conn.cursor()
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='export_tokens'"
    )
    return {r[0] for r in cur.fetchall()}


def _revision(conn) -> str:
    cur = conn.cursor()
    cur.execute("SELECT version_num FROM alembic_version")
    return cur.fetchone()[0]


def test_existing_tokens_survive_backfill_and_drop(database) -> None:
    assert _alembic(database, PREDECESSOR).returncode == 0
    conn = _connect(database)
    public, internal, personal, mixed = "pub-" + "a" * 40, "int-" + "b" * 40, "per-" + "c" * 40, "mix-" + "d" * 40
    _seed(
        conn,
        [
            ("PUBLIC", public, None),  # legacy writer after the expand migration: hash missing
            ("INTERNAL", internal, _sha(internal)),  # correct hash from the expand backfill
            ("PERSONAL", personal, None),
            ("PUBLIC", mixed, _sha(mixed)),
        ],
    )
    assert "token" in _columns(conn)

    result = _alembic(database, CONTRACT)
    assert result.returncode == 0, result.stderr[-2000:]

    assert "token" not in _columns(conn)
    assert _revision(conn) == CONTRACT

    async def lookup() -> dict[str, bool]:
        engine = create_async_engine(
            database.set(drivername="postgresql+asyncpg").render_as_string(hide_password=False)
        )
        try:
            async with async_sessionmaker(engine)() as session:
                repo = SqlExportTokenRepository(session)
                found = {
                    plain: await repo.get_by_token(plain) is not None
                    for plain in (public, internal, personal, mixed, "unknown-" + "e" * 40)
                }
            return found
        finally:
            await engine.dispose()

    found = asyncio.run(lookup())
    assert [found[t] for t in (public, internal, personal, mixed)] == [True] * 4  # URLs unchanged
    assert found["unknown-" + "e" * 40] is False


def test_tampered_hash_aborts_the_whole_migration(database) -> None:
    assert _alembic(database, PREDECESSOR).returncode == 0
    conn = _connect(database)
    good, bad = "ok-" + "f" * 40, "bad-" + "g" * 40
    _seed(conn, [("PUBLIC", good, None), ("INTERNAL", bad, _sha("something-else"))])

    result = _alembic(database, CONTRACT)

    assert result.returncode != 0
    assert "Export token hash mismatch" in result.stderr
    # Fully rolled back: plaintext still there, revision unchanged, backfill undone.
    assert _revision(conn) == PREDECESSOR
    assert "token" in _columns(conn)
    cur = conn.cursor()
    cur.execute("SELECT token, token_hash FROM export_tokens ORDER BY token")
    rows = dict(cur.fetchall())
    assert rows[good] is None  # the UPDATE ahead of the check was rolled back as well
    assert rows[bad] == _sha("something-else")
    cur.execute("SELECT count(*) FROM pg_policies WHERE qual LIKE '%%token_hash%%'")
    # No policy was rewritten to the hash-only form.
    assert cur.fetchone()[0] == 0


def test_empty_installation_migrates(database) -> None:
    assert _alembic(database, PREDECESSOR).returncode == 0
    assert _alembic(database, CONTRACT).returncode == 0
    assert "token" not in _columns(_connect(database))
