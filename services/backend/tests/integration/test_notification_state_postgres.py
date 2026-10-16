# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Per-user notification state, including pre-migration global state (#601).

TEST_DATABASE_URL must identify a migrated disposable PostgreSQL test database.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.notification import SqlNotificationRepository

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
async def sessions():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def seeded(sessions):
    district = uuid.uuid4()
    ids = {k: uuid.uuid4() for k in ("fresh", "legacy_read", "legacy_dismissed")}
    subs = {k: f"{k}-{uuid.uuid4().hex[:8]}" for k in ("a", "b")}
    now = datetime.now(UTC)
    async with sessions() as db, db.begin():
        await db.execute(
            text(
                "INSERT INTO districts (id, name, created_at, updated_at) VALUES (:i, 'B', :n, :n)"
            ),
            {"i": district, "n": now},
        )
        for sub in subs.values():
            await db.execute(
                text(
                    "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
                    "VALUES (:i, :s, :e, :s, false, :n, :n)"
                ),
                {"i": uuid.uuid4(), "s": sub, "e": f"{sub}@example.test", "n": now},
            )
        for key, nid in ids.items():
            await db.execute(
                text(
                    "INSERT INTO notifications (id, district_id, type, title, body, payload, "
                    "created_at, read_at, dismissed_at) VALUES (:i, :d, 'SYSTEM', :t, '', '{}', :n, "
                    ":r, :x)"
                ),
                {
                    "i": nid,
                    "d": district,
                    "t": key,
                    "n": now,
                    "r": now if key == "legacy_read" else None,
                    "x": now if key == "legacy_dismissed" else None,
                },
            )
    yield district, ids, subs
    async with sessions() as db, db.begin():
        await db.execute(text("DELETE FROM districts WHERE id = :i"), {"i": district})
        for sub in subs.values():
            await db.execute(text("DELETE FROM users WHERE sub = :s"), {"s": sub})


async def test_state_is_per_user_and_legacy_state_is_honoured(sessions, seeded) -> None:
    district, ids, subs = seeded
    async with sessions() as db, db.begin():
        repo = SqlNotificationRepository(db)
        await repo.mark_dismissed(ids["fresh"], subs["a"])

        a_items, _ = await repo.list_by_district(district, subs["a"])
        b_items, _ = await repo.list_by_district(district, subs["b"])
        a_unread, _ = await repo.list_by_district(district, subs["a"], unread_only=True)

    assert {n.title for n in a_items} == {
        "legacy_read"
    }  # dismissed fresh + legacy_dismissed hidden
    assert {n.title for n in b_items} == {"fresh", "legacy_read"}  # B unaffected by A's dismiss
    assert a_unread == []  # legacy_read stays read
    assert next(n for n in b_items if n.title == "legacy_read").read_at is not None


async def test_mark_all_read_skips_legacy_acknowledged_rows(sessions, seeded) -> None:
    district, _ids, subs = seeded
    async with sessions() as db, db.begin():
        repo = SqlNotificationRepository(db)
        assert await repo.mark_all_read(district, subs["a"]) == 1  # only "fresh"
        a_unread, _ = await repo.list_by_district(district, subs["a"], unread_only=True)
        b_unread, _ = await repo.list_by_district(district, subs["b"], unread_only=True)

    assert a_unread == []
    assert {n.title for n in b_unread} == {"fresh"}
