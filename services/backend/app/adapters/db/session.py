# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""app/adapters/db/session.py: Module."""

from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.adapters.db.domain_audit import record_domain_audit
from app.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


class AuditedSession(Session):
    """Session that records domain audit entries on every flush."""


event.listen(AuditedSession, "after_flush", record_domain_audit)

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, sync_session_class=AuditedSession
)


def _set_tenant_gucs(connection, **kwargs):
    """Set PostgreSQL tenant GUCs from Python TenantContext contextvars.

    Called on each new transaction so that RLS policies can read
    ``current_setting('app.current_user_sub')`` etc.
    """
    # Deferred import to avoid circular dependency at module level
    from app.tenant import TenantContext as TC

    user_sub = TC.get_user_sub()
    if user_sub is not None:
        connection.execute(
            text("SELECT set_config('app.current_user_sub', :val, true)"),
            {"val": user_sub},
        )
    user_roles = TC.get_user_roles()
    if user_roles:
        connection.execute(
            text("SELECT set_config('app.current_user_roles', :val, true)"),
            {"val": ",".join(user_roles)},
        )
    if "SYSTEM_WORKER" in (user_roles or []):
        connection.execute(
            text("SELECT set_config('app.is_system_worker', 'true', true)"),
        )
    district_id = TC.get_district()
    if district_id is not None:
        connection.execute(
            text("SELECT set_config('app.current_district_id', :val, true)"),
            {"val": str(district_id)},
        )
    congregation_id = TC.get_congregation()
    if congregation_id is not None:
        connection.execute(
            text("SELECT set_config('app.current_congregation_id', :val, true)"),
            {"val": str(congregation_id)},
        )
    tenant_id = TC.get_tenant()
    if tenant_id is not None:
        connection.execute(
            text("SELECT set_config('app.current_tenant_id', :val, true)"),
            {"val": str(tenant_id)},
        )


event.listen(engine.sync_engine, "begin", _set_tenant_gucs)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
