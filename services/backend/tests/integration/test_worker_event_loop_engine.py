# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Regression for #464: consecutive asyncio.run task bodies share one pooled engine.

Celery tasks bridge into async code with ``asyncio.run`` per execution. Pooled
asyncpg connections are bound to the loop that created them, so the second run
in the same process failed with "Event loop is closed" / "different loop".
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db import session as session_module
from app.adapters.db.session import AuditedSession, _set_tenant_gucs
from app.application.tasks import _run_as_system_worker


def test_consecutive_asyncio_run_task_bodies_reuse_module_engine(monkeypatch) -> None:
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    # Same configuration as the production module engine (default QueuePool).
    engine = create_async_engine(db_url, pool_pre_ping=True)
    event.listen(engine.sync_engine, "begin", _set_tenant_gucs)
    factory = async_sessionmaker(engine, expire_on_commit=False, sync_session_class=AuditedSession)
    monkeypatch.setattr(session_module, "engine", engine)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", factory)

    async def task_body() -> str | None:
        async with session_module.AsyncSessionLocal() as db:
            return await db.scalar(text("SELECT current_setting('app.is_system_worker', true)"))

    try:
        for _ in range(3):
            assert asyncio.run(_run_as_system_worker(task_body())) == "true"
    finally:
        asyncio.run(engine.dispose())
