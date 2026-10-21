# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""A write is acknowledged only after its transaction committed (#648).

FastAPI's default dependency scope runs the exit code of a ``yield`` dependency
after the response exists, so a failed ``commit()`` still reached the client as a
success while the change and its audit rows rolled back.
"""

import httpx
import pytest
from fastapi import Depends, FastAPI

from app.adapters.api import deps
from app.adapters.db import session as session_module


class _FakeSession:
    def __init__(self, fail_commit: bool) -> None:
        self.fail_commit = fail_commit
        self.events: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.events.append("close")

    async def commit(self):
        self.events.append("commit")
        if self.fail_commit:
            raise RuntimeError("commit rejected")

    async def rollback(self):
        self.events.append("rollback")


def _app(db_type) -> FastAPI:
    app = FastAPI()

    @app.post("/write")
    async def write(db: db_type):  # type: ignore[valid-type]
        return {"ok": True}

    return app


async def _post(app: FastAPI) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/write")


@pytest.mark.asyncio
async def test_a_failed_commit_is_an_error_not_a_success(monkeypatch):
    fake = _FakeSession(fail_commit=True)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", lambda: fake)

    response = await _post(_app(deps.DbSession))

    assert response.status_code == 500
    assert fake.events == ["commit", "rollback", "close"]


@pytest.mark.asyncio
async def test_a_successful_commit_is_acknowledged(monkeypatch):
    fake = _FakeSession(fail_commit=False)
    monkeypatch.setattr(session_module, "AsyncSessionLocal", lambda: fake)

    response = await _post(_app(deps.DbSession))

    assert response.status_code == 200
    assert fake.events == ["commit", "close"]


@pytest.mark.asyncio
async def test_repository_dependencies_share_the_function_scoped_session(monkeypatch):
    """One request uses one session: scope must match across every consumer."""
    sessions: list[_FakeSession] = []

    def factory():
        sessions.append(_FakeSession(fail_commit=False))
        return sessions[-1]

    monkeypatch.setattr(session_module, "AsyncSessionLocal", factory)
    app = FastAPI()

    @app.post("/write")
    async def write(
        db: deps.DbSession,
        repository=Depends(deps.get_leader_repository),
        service=Depends(deps.get_notification_service),
    ):
        assert repository._session is db and service is not None
        return {"ok": True}

    response = await _post(app)

    assert response.status_code == 200
    assert len(sessions) == 1


def test_no_module_declares_the_session_dependency_with_the_default_scope():
    """A consumer with another scope would open a second session and commit after the response."""
    import re
    from pathlib import Path

    app_root = Path(session_module.__file__).resolve().parents[2]
    offenders = []
    for path in app_root.rglob("*.py"):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if re.search(r"Depends\(\s*get_db_session\b", line) and 'scope="function"' not in line:
                offenders.append(f"{path.relative_to(app_root)}:{number}")
    assert offenders == []
