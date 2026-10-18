# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""End-to-end upgrade of the irreversible export-token contract migration (#602).

Each test creates a throwaway database, migrates it to the immediate
predecessor revision, seeds *existing* plaintext tokens as an old installation
would have them, runs ``alembic upgrade head`` for real and inspects the result.

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

    result = _alembic(database, "head")
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

    result = _alembic(database, "head")

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
    assert _alembic(database, "head").returncode == 0
    assert "token" not in _columns(_connect(database))


def _app_role_connection(url):
    """Connect with the actual non-owner, non-BYPASSRLS runtime role."""
    password = os.getenv("RLS_TEST_APP_PASSWORD")
    if not password:
        pytest.fail("RLS_TEST_APP_PASSWORD is required for the contract runtime-role test")
    connection = psycopg2.connect(
        host=url.host,
        port=url.port,
        user=os.getenv("APP_DB_USER", "nak_app"),
        password=password,
        dbname=url.database,
    )
    connection.autocommit = False
    return connection


def _runtime_visible_slot_ids(url, token: str, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Set bearer context transaction-locally, then query as NOBYPASSRLS."""
    connection = _app_role_connection(url)
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT current_user")
            assert cur.fetchone()[0] == os.getenv("APP_DB_USER", "nak_app")
            cur.execute(
                "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )
            assert cur.fetchone() == (False, False)
            cur.execute("SELECT set_config('app.current_export_token', %s, true)", (token,))
            cur.execute(
                "SELECT id FROM planning_slots WHERE id = ANY(%s::uuid[])",
                ([str(slot_id) for slot_id in ids],),
            )
            return {row[0] for row in cur.fetchall()}
    finally:
        connection.rollback()
        connection.close()


def test_runtime_role_token_visibility_after_contract_upgrade(database) -> None:
    """PUBLIC, INTERNAL and subject tokens stay tenant-scoped; revoked tokens lose access."""
    assert os.getenv("RLS_TEST_APP_PASSWORD"), "application-role credentials required"
    assert _alembic(database, PREDECESSOR).returncode == 0
    owner = _connect(database)
    token_values = {
        kind: f"{kind.lower()}-{uuid.uuid4().hex}{uuid.uuid4().hex}"
        for kind in ("PUBLIC", "INTERNAL", "PERSONAL", "REVOKED", "FOREIGN")
    }
    own_ids = _seed(
        owner,
        [
            ("PUBLIC", token_values["PUBLIC"], None),
            ("INTERNAL", token_values["INTERNAL"], None),
            ("PERSONAL", token_values["PERSONAL"], None),
            ("PUBLIC", token_values["REVOKED"], None),
        ],
    )
    foreign_ids = _seed(owner, [("INTERNAL", token_values["FOREIGN"], None)])
    cur = owner.cursor()
    cur.execute("SELECT district_id FROM export_tokens WHERE id=%s", (str(own_ids[0]),))
    own_district = cur.fetchone()[0]
    cur.execute("SELECT district_id FROM export_tokens WHERE id=%s", (str(foreign_ids[0]),))
    foreign_district = cur.fetchone()[0]
    own_slot, foreign_slot = uuid.uuid4(), uuid.uuid4()
    for slot_id, district in [(own_slot, own_district), (foreign_slot, foreign_district)]:
        cur.execute(
            "INSERT INTO planning_slots "
            "(id, district_id, planning_date, planning_time, status, created_at, updated_at) "
            "VALUES (%s, %s, '2026-12-24', '09:30', 'ACTIVE', now(), now())",
            (str(slot_id), str(district)),
        )
    result = _alembic(database, "head")
    assert result.returncode == 0, result.stderr[-1000:]
    assert "token" not in _columns(owner)

    # An application role may use a valid bearer token, but must never see a foreign district.
    for kind in ("PUBLIC", "INTERNAL", "PERSONAL"):
        assert _runtime_visible_slot_ids(
            database, token_values[kind], [own_slot, foreign_slot]
        ) == {own_slot}, kind

    # The owner revokes the token; a fresh runtime transaction must not see either tenant.
    cur.execute("DELETE FROM export_tokens WHERE id=%s", (str(own_ids[3]),))
    for token in (token_values["REVOKED"], "missing-" + uuid.uuid4().hex):
        assert _runtime_visible_slot_ids(database, token, [own_slot, foreign_slot]) == set()
    assert _runtime_visible_slot_ids(
        database, token_values["FOREIGN"], [own_slot, foreign_slot]
    ) == {foreign_slot}

    # Absence of a token is not a privileged state.
    assert _runtime_visible_slot_ids(database, "", [own_slot, foreign_slot]) == set()


def test_contract_policies_and_functions_drop_plaintext_dependency(database) -> None:
    """Inspect active PostgreSQL definitions, not just Python migration source."""
    import re

    assert _alembic(database, PREDECESSOR).returncode == 0
    owner = _connect(database)
    _seed(owner, [("PUBLIC", "pub-" + uuid.uuid4().hex, None)])
    result = _alembic(database, "head")
    assert result.returncode == 0, result.stderr[-1000:]

    cur = owner.cursor()
    cur.execute("SELECT qual, with_check FROM pg_policies")
    policy_sql = [part for row in cur.fetchall() for part in row if part]
    cur.execute(
        "SELECT pg_get_functiondef(p.oid) FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid=p.pronamespace "
        "WHERE n.nspname='public' AND p.prokind='f'"
    )
    function_sql = [row[0] for row in cur.fetchall() if "app.current_export_token" in row[0]]
    definitions = [*policy_sql, *function_sql]
    assert definitions, "expected actual export-token dependent SQL definitions"
    assert any("token_hash" in sql for sql in definitions)
    for statement in definitions:
        assert re.search(r"\\b(?:et|export_tokens)\\s*\\.\\s*token\\b", statement, re.I) is None
    assert "token" not in _columns(owner)
