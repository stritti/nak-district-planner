# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""End-to-end test of the leader assignments revision on existing data (step 4).

Each test creates a throwaway database, migrates it to the predecessor revision, seeds
leaders as an old installation would have them, upgrades for real and inspects the result.
TEST_DATABASE_URL must be a PostgreSQL superuser URL (``postgresql+asyncpg://...``).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")
from sqlalchemy import make_url  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PREDECESSOR = "20261021_duty_identity_interval"
REVISION = "20261022_leader_assignments"

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
def database():
    base = make_url(os.environ["TEST_DATABASE_URL"])
    name = f"leaders_{uuid.uuid4().hex[:10]}"
    admin = psycopg2.connect(
        host=base.host, port=base.port, user=base.username, password=base.password, dbname=base.database
    )
    admin.autocommit = True
    admin.cursor().execute(f'CREATE DATABASE "{name}"')
    yield base.set(database=name)
    admin.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    admin.close()


def _alembic(url, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": url.render_as_string(hide_password=False), "MIGRATION_DATABASE_URL": ""}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args], cwd=BACKEND_ROOT, env=env,
        capture_output=True, text=True, check=False,
    )


def _connect(url):
    conn = psycopg2.connect(host=url.host, port=url.port, user=url.username, password=url.password, dbname=url.database)
    conn.autocommit = True
    return conn


def _seed_legacy(conn):
    """Leaders with home congregation / special role in all combinations, incl. odd legacy ones."""
    cur = conn.cursor()
    district, congregation = str(uuid.uuid4()), str(uuid.uuid4())
    cur.execute("INSERT INTO districts (id, name, created_at, updated_at) VALUES (%s, 'B', now(), now())", (district,))
    cur.execute(
        "INSERT INTO congregations (id, name, district_id, created_at, updated_at) VALUES (%s, 'G', %s, now(), now())",
        (congregation, district),
    )
    leaders = {
        "vorsteher": (congregation, "Gemeindevorsteher"),
        "bezirk": (None, "Bezirksvorsteher"),
        "plain": (congregation, None),
        "district_plain": (None, None),
        "odd": (congregation, "Bezirksvorsteher"),  # not expressible in the new rules, must still migrate
    }
    ids = {}
    for key, (cong, role) in leaders.items():
        ids[key] = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO leaders (id, name, district_id, congregation_id, special_role) VALUES (%s, %s, %s, %s, %s)",
            (ids[key], key, district, cong, role),
        )
    return ids, congregation


def _canonical(policies) -> list[tuple]:
    """Policy text without PostgreSQL's cosmetic re-rendering of ANY(ARRAY[...]) casts."""
    def clean(expression):
        return re.sub(r"[\s()]|::[a-z ]+(\[\])?", "", expression or "")

    return sorted((name, cmd, clean(qual), clean(check)) for name, cmd, qual, check in policies)


def _leader_policies(conn):
    cur = conn.cursor()
    cur.execute("SELECT policyname, cmd, qual, with_check FROM pg_policies WHERE tablename='leaders'")
    return cur.fetchall()


def test_existing_leaders_become_home_assignments(database) -> None:
    assert _alembic(database, "upgrade", PREDECESSOR).returncode == 0
    conn = _connect(database)
    ids, congregation = _seed_legacy(conn)

    result = _alembic(database, "upgrade", REVISION)
    assert result.returncode == 0, result.stderr[-2000:]

    cur = conn.cursor()
    cur.execute("SELECT leader_id, congregation_id, role, is_home FROM leader_assignments")
    rows = {str(r[0]): (str(r[1]) if r[1] else None, r[2], r[3]) for r in cur.fetchall()}
    assert rows[ids["vorsteher"]] == (congregation, "Gemeindevorsteher", True)
    assert rows[ids["bezirk"]] == (None, "Bezirksvorsteher", True)
    assert rows[ids["plain"]] == (congregation, None, True)
    assert rows[ids["district_plain"]] == (None, None, True)
    assert rows[ids["odd"]] == (congregation, "Bezirksvorsteher", True)  # carried over unchanged
    cur.execute("SELECT count(*) FROM leaders")
    assert len(rows) == cur.fetchone()[0]  # exactly one assignment per leader, seed data included
    cur.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='leaders' "
        "AND column_name IN ('congregation_id','special_role')"
    )
    assert cur.fetchall() == []


def test_the_downgrade_restores_columns_and_policies_from_the_home_assignment(database) -> None:
    assert _alembic(database, "upgrade", PREDECESSOR).returncode == 0
    conn = _connect(database)
    ids, congregation = _seed_legacy(conn)
    before = _canonical(_leader_policies(conn))
    assert _alembic(database, "upgrade", REVISION).returncode == 0
    cur = conn.cursor()
    # An additional assignment exists only in the new model; the downgrade drops it.
    other = str(uuid.uuid4())
    cur.execute("SELECT district_id FROM leaders WHERE id=%s", (ids["plain"],))
    district = cur.fetchone()[0]
    cur.execute("INSERT INTO congregations (id, name, district_id, created_at, updated_at) VALUES (%s, 'G2', %s, now(), now())", (other, district))
    cur.execute(
        "INSERT INTO leader_assignments (id, leader_id, district_id, congregation_id, role, is_home, created_at, updated_at) "
        "VALUES (gen_random_uuid(), %s, %s, %s, 'Gemeindevorsteher', false, now(), now())",
        (ids["plain"], district, other),
    )

    result = _alembic(database, "downgrade", "-1")
    assert result.returncode == 0, result.stderr[-2000:]

    cur.execute("SELECT id, congregation_id, special_role FROM leaders")
    restored = {str(r[0]): (str(r[1]) if r[1] else None, r[2]) for r in cur.fetchall()}
    assert restored[ids["vorsteher"]] == (congregation, "Gemeindevorsteher")
    assert restored[ids["bezirk"]] == (None, "Bezirksvorsteher")
    assert restored[ids["plain"]] == (congregation, None)  # the home values, not the extra assignment
    cur.execute("SELECT to_regclass('leader_assignments')")
    assert cur.fetchone()[0] is None
    assert _canonical(_leader_policies(conn)) == before  # same policies as before the revision


def test_an_empty_installation_migrates_both_ways(database) -> None:
    assert _alembic(database, "upgrade", REVISION).returncode == 0
    assert _alembic(database, "downgrade", "-1").returncode == 0
    assert _alembic(database, "upgrade", REVISION).returncode == 0
