"""Shared test setup.

The application's global async engine keeps a connection pool, and asyncpg
connections are bound to the event loop that opened them.  Tests run the app
on many short-lived loops (each ``TestClient`` request, each pytest-asyncio
test), so pooled connections leak into foreign or already closed loops.  The
pool then cannot terminate them cleanly, which surfaces as ``RuntimeWarning:
coroutine 'Connection._cancel' was never awaited`` and "attached to a
different loop" errors.  Bind the app's session factory to an unpooled engine
for the test run instead; the production engine is left untouched.
"""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.db import session as db_session

_test_engine = create_async_engine(db_session.engine.url, poolclass=NullPool)
event.listen(_test_engine.sync_engine, "begin", db_session._set_tenant_gucs)
db_session.AsyncSessionLocal.configure(bind=_test_engine)
db_session.engine = _test_engine
