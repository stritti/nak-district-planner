# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""A commit rejected by PostgreSQL is answered as an error and leaves nothing behind (#648).

The rejection is real: a deferred foreign key is only checked at COMMIT, after the
route function returned successfully.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.api import deps
from app.adapters.db import session as session_module

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


@pytest.fixture
async def tables():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    parent = f"commit_parent_{uuid.uuid4().hex[:8]}"
    child = f"commit_child_{uuid.uuid4().hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE TABLE {parent} (id int PRIMARY KEY)"))
        await conn.execute(
            text(
                f"CREATE TABLE {child} (id int PRIMARY KEY, parent_id int REFERENCES {parent}(id) "
                "DEFERRABLE INITIALLY DEFERRED)"
            )
        )
    yield engine, parent, child
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE {child}"))
        await conn.execute(text(f"DROP TABLE {parent}"))
    await engine.dispose()


async def _count(engine, table: str) -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM {table}"))).scalar_one()  # noqa: S608


def _app(child: str) -> FastAPI:
    app = FastAPI()

    @app.post("/child/{parent_id}")
    async def write(parent_id: int, db: deps.DbSession):
        await db.execute(text(f"INSERT INTO {child} VALUES (1, :p)"), {"p": parent_id})  # noqa: S608
        return {"ok": True}

    return app


async def _post(app: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path)


async def test_a_commit_rejected_by_postgresql_is_not_acknowledged(tables, monkeypatch):
    engine, _parent, child = tables
    monkeypatch.setattr(session_module, "AsyncSessionLocal", async_sessionmaker(engine, expire_on_commit=False))

    response = await _post(_app(child), "/child/999")  # no such parent: fails at COMMIT

    assert response.status_code == 500
    assert await _count(engine, child) == 0


async def test_a_valid_write_is_committed_and_acknowledged(tables, monkeypatch):
    engine, parent, child = tables
    monkeypatch.setattr(session_module, "AsyncSessionLocal", async_sessionmaker(engine, expire_on_commit=False))
    async with engine.begin() as conn:
        await conn.execute(text(f"INSERT INTO {parent} VALUES (7)"))  # noqa: S608

    response = await _post(_app(child), "/child/7")

    assert response.status_code == 200
    assert await _count(engine, child) == 1
