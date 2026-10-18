# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Real PostgreSQL rollback guarantee when atomic domain audit persistence fails (#648)."""

from __future__ import annotations

import os
import uuid
from datetime import date, time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.orm_models.planning_slot import PlanningSlotORM
from app.adapters.db.session import AuditedSession
from app.domain.models.planning_slot import PlanningSlotStatus

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL is not configured"
)


async def test_atomic_business_write_rolls_back_when_audit_insert_fails() -> None:
    """Simulate a database-side audit insert error, not a mocked repository error."""
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    sessions = async_sessionmaker(
        engine, expire_on_commit=False, sync_session_class=AuditedSession
    )
    district_id, slot_id = uuid.uuid4(), uuid.uuid4()
    trigger = "audit_inject_failure_648"
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO districts (id, name, created_at, updated_at) "
                    "VALUES (:id, :name, now(), now())"
                ),
                {"id": district_id, "name": f"Audit failure {district_id.hex}"},
            )
            await conn.execute(
                text(
                    "CREATE OR REPLACE FUNCTION audit_inject_failure_648() "
                    "RETURNS trigger LANGUAGE plpgsql AS "
                    "$$ BEGIN RAISE EXCEPTION 'forced audit insert failure'; END $$"
                )
            )
            await conn.execute(
                text(
                    "CREATE TRIGGER audit_inject_failure_648 "
                    "BEFORE INSERT ON audit_logs "
                    "FOR EACH ROW EXECUTE FUNCTION audit_inject_failure_648()"
                )
            )

        with pytest.raises(DBAPIError, match="forced audit insert failure"):
            async with sessions() as session:
                session.add(
                    PlanningSlotORM(
                        id=slot_id,
                        district_id=district_id,
                        planning_date=date(2031, 2, 3),
                        planning_time=time(9, 30),
                        status=PlanningSlotStatus.ACTIVE,
                        category="Gottesdienst",
                    )
                )
                await session.commit()

        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT count(*) FROM planning_slots WHERE id=:id"), {"id": slot_id}
            )
            assert result.scalar_one() == 0, "Mutation committed without its mandatory audit"
            result = await conn.execute(
                text("SELECT count(*) FROM audit_logs WHERE resource_id=:id"), {"id": slot_id}
            )
            assert result.scalar_one() == 0
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f"DROP TRIGGER IF EXISTS {trigger} ON audit_logs"))
            await conn.execute(text("DROP FUNCTION IF EXISTS audit_inject_failure_648()"))
            await conn.execute(
                text("DELETE FROM planning_slots WHERE id=:id"), {"id": slot_id}
            )
            await conn.execute(
                text("DELETE FROM districts WHERE id=:id"), {"id": district_id}
            )
        await engine.dispose()
