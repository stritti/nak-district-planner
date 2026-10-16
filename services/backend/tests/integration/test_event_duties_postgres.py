# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""PostgreSQL coverage for duty capacity, tenant RLS and subject feeds."""

from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from contextlib import contextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.adapters.db.repositories.event_duties import SqlEventDutiesRepository
from app.application.event_duties import DutyConflictError, EventDutiesService
from tests.integration.test_rls_postgres import (
    APP_PASSWORD,
    APP_ROLE,
    OWNER_DSN,
    _visible_ids,
    app_session,
    psycopg2,
)

pytest_plugins = ("tests.integration.test_rls_postgres",)

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not (OWNER_DSN and APP_PASSWORD and os.getenv("TEST_DATABASE_URL")),
        reason="PostgreSQL integration environment not configured",
    ),
]


@pytest.fixture
def duty_rows(owner, data):
    """Seed all duty table kinds in two tenants plus a subject-bound feed."""
    ids = {
        name: uuid.uuid4()
        for name in (
            "slot_a",
            "slot_b",
            "category_a",
            "category_b",
            "config_a",
            "config_b",
            "suggestion_a",
            "suggestion_b",
            "assignment_a",
            "assignment_b",
            "token",
        )
    }
    subject = data.sub(f"duty-subject-{uuid.uuid4().hex[:8]}")
    token = f"duty-{uuid.uuid4().hex}"
    with owner.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id,sub,email,username,is_superadmin,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,false,now(),now())",
            (str(uuid.uuid4()), subject, f"{subject}@example.org", subject),
        )
        cur.execute(
            "INSERT INTO memberships (id,user_sub,role,scope_type,scope_id,created_at,updated_at) "
            "VALUES (%s,%s,'PLANNER','DISTRICT',%s,now(),now())",
            (str(uuid.uuid4()), subject, str(data.a.district_id)),
        )
        for suffix, tenant in (("a", data.a), ("b", data.b)):
            cur.execute(
                "INSERT INTO planning_slots "
                "(id,district_id,congregation_id,category,planning_date,planning_time,status,"
                "applicability,created_at,updated_at) VALUES "
                "(%s,%s,%s,'Gottesdienst','2027-03-01','10:00','ACTIVE','{}',now(),now())",
                (
                    str(ids[f"slot_{suffix}"]),
                    str(tenant.district_id),
                    str(tenant.congregation_id),
                ),
            )
            cur.execute(
                "INSERT INTO event_duty_categories "
                "(id,district_id,congregation_id,code,label,event_categories,enabled,capacity) "
                "VALUES (%s,%s,NULL,%s,'Testdienst','{}',true,1)",
                (
                    str(ids[f"category_{suffix}"]),
                    str(tenant.district_id),
                    f"test-{suffix}-{uuid.uuid4().hex[:8]}",
                ),
            )
            cur.execute(
                "INSERT INTO event_type_duty_configurations "
                "(id,district_id,congregation_id,duty_category_id,event_categories,enabled,capacity) "
                "VALUES (%s,%s,%s,%s,'{}',true,1)",
                (
                    str(ids[f"config_{suffix}"]),
                    str(tenant.district_id),
                    str(tenant.congregation_id),
                    str(ids[f"category_{suffix}"]),
                ),
            )
            cur.execute(
                "INSERT INTO duty_name_suggestions "
                "(id,district_id,congregation_id,duty_category_id,display_name,normalized_name,hidden) "
                "VALUES (%s,%s,%s,%s,%s,%s,false)",
                (
                    str(ids[f"suggestion_{suffix}"]),
                    str(tenant.district_id),
                    str(tenant.congregation_id),
                    str(ids[f"category_{suffix}"]),
                    f"Name {suffix.upper()}",
                    f"name {suffix}",
                ),
            )
        cur.execute(
            "INSERT INTO event_duty_assignments "
            "(id,planning_slot_id,duty_category_id,district_id,congregation_id,display_name,"
            "duty_label,linked_user_sub,normalized_name,suggestion_id) "
            "VALUES (%s,%s,%s,%s,%s,'Eigener Dienst','Testdienst',%s,NULL,NULL)",
            (
                str(ids["assignment_a"]),
                str(ids["slot_a"]),
                str(ids["category_a"]),
                str(data.a.district_id),
                str(data.a.congregation_id),
                subject,
            ),
        )
        cur.execute(
            "INSERT INTO event_duty_assignments "
            "(id,planning_slot_id,duty_category_id,district_id,congregation_id,display_name,"
            "duty_label,linked_user_sub,normalized_name,suggestion_id) "
            "VALUES (%s,%s,%s,%s,%s,'Fremder Dienst','Testdienst',NULL,'fremder dienst',NULL)",
            (
                str(ids["assignment_b"]),
                str(ids["slot_b"]),
                str(ids["category_b"]),
                str(data.b.district_id),
                str(data.b.congregation_id),
            ),
        )
        cur.execute(
            "INSERT INTO export_tokens "
            "(id,token_hash,label,token_type,district_id,congregation_id,leader_id,subject_sub,created_at) "
            "VALUES (%s,%s,'Persönlicher Kalender','INTERNAL',%s,NULL,NULL,%s,now())",
            (str(ids["token"]), hashlib.sha256(token.encode()).hexdigest(), str(data.a.district_id), subject),
        )
    yield ids, subject, token
    with owner.cursor() as cur:
        cur.execute("DELETE FROM export_tokens WHERE id=%s", (str(ids["token"]),))
        cur.execute(
            "DELETE FROM event_duty_assignments WHERE id=ANY(%s::uuid[])",
            ([str(ids["assignment_a"]), str(ids["assignment_b"])],),
        )
        cur.execute(
            "DELETE FROM duty_name_suggestions WHERE id=ANY(%s::uuid[])",
            ([str(ids["suggestion_a"]), str(ids["suggestion_b"])],),
        )
        cur.execute(
            "DELETE FROM event_type_duty_configurations WHERE id=ANY(%s::uuid[])",
            ([str(ids["config_a"]), str(ids["config_b"])],),
        )
        cur.execute(
            "DELETE FROM planning_slots WHERE id=ANY(%s::uuid[])",
            ([str(ids["slot_a"]), str(ids["slot_b"])],),
        )
        cur.execute(
            "DELETE FROM event_duty_categories WHERE id=ANY(%s::uuid[])",
            ([str(ids["category_a"]), str(ids["category_b"])],),
        )
        cur.execute("DELETE FROM memberships WHERE user_sub=%s", (subject,))
        cur.execute("DELETE FROM users WHERE sub=%s", (subject,))


@contextmanager
def export_session(token: str):
    from psycopg2.extensions import make_dsn

    connection = psycopg2.connect(make_dsn(OWNER_DSN, user=APP_ROLE, password=APP_PASSWORD))
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.current_export_token', %s, true)", (token,))
            yield cur
    finally:
        connection.rollback()
        connection.close()


def test_duty_rls_reads_only_own_tenant_rows(data, duty_rows):
    ids, _, _ = duty_rows
    cases = (
        ("event_duty_categories", "category_a", "category_b"),
        ("event_type_duty_configurations", "config_a", "config_b"),
        ("duty_name_suggestions", "suggestion_a", "suggestion_b"),
        ("event_duty_assignments", "assignment_a", "assignment_b"),
    )
    with app_session(data.sub("viewer-a")) as cur:
        for table, own, foreign in cases:
            assert _visible_ids(cur, table, [ids[own], ids[foreign]]) == {ids[own]}
    with app_session(data.sub("outsider")) as cur:
        for table, own, foreign in cases:
            assert _visible_ids(cur, table, [ids[own], ids[foreign]]) == set()


def test_duty_rls_separates_planner_and_admin_writes(data, duty_rows):
    ids, _, _ = duty_rows
    with app_session(data.sub("viewer-a")) as cur:
        cur.execute(
            "UPDATE event_duty_assignments SET display_name='Nicht erlaubt' WHERE id=%s",
            (str(ids["assignment_a"]),),
        )
        assert cur.rowcount == 0
    with app_session(data.sub("planner-a")) as cur:
        cur.execute(
            "UPDATE event_duty_assignments SET display_name='Erlaubt' WHERE id=%s",
            (str(ids["assignment_a"]),),
        )
        assert cur.rowcount == 1
        cur.execute(
            "UPDATE event_duty_categories SET label='Nicht erlaubt' WHERE id=%s",
            (str(ids["category_a"]),),
        )
        assert cur.rowcount == 0
    with app_session(data.sub("admin-a")) as cur:
        cur.execute(
            "UPDATE event_duty_categories SET label='Erlaubt' WHERE id=%s",
            (str(ids["category_a"]),),
        )
        assert cur.rowcount == 1
        cur.execute(
            "UPDATE event_duty_assignments SET display_name='Fremd' WHERE id=%s",
            (str(ids["assignment_b"]),),
        )
        assert cur.rowcount == 0


def test_eligible_user_picker_does_not_broaden_membership_rows(owner, data, duty_rows):
    _, subject, _ = duty_rows
    foreign_subject = data.sub(f"duty-foreign-candidate-{uuid.uuid4().hex[:8]}")
    with owner.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id,sub,email,username,is_superadmin,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,false,now(),now())",
            (
                str(uuid.uuid4()),
                foreign_subject,
                f"{foreign_subject}@example.org",
                foreign_subject,
            ),
        )
        cur.execute(
            "INSERT INTO memberships (id,user_sub,role,scope_type,scope_id,created_at,updated_at) "
            "VALUES (%s,%s,'VIEWER','CONGREGATION',%s,now(),now())",
            (str(uuid.uuid4()), foreign_subject, str(data.b.congregation_id)),
        )
    try:
        with app_session(subject) as cur:
            cur.execute("SELECT DISTINCT user_sub FROM memberships")
            assert {row[0] for row in cur.fetchall()} == {subject}

            cur.execute(
                "SELECT * FROM eligible_duty_users(%s,%s)",
                (str(data.a.district_id), str(data.a.congregation_id)),
            )
            assert [column.name for column in cur.description] == ["sub", "display_name"]
            assert subject in {row[0] for row in cur.fetchall()}

            cur.execute(
                "SELECT * FROM eligible_duty_users(%s,%s)",
                (str(data.a.district_id), str(data.b.congregation_id)),
            )
            assert foreign_subject not in {row[0] for row in cur.fetchall()}
    finally:
        with owner.cursor() as cur:
            cur.execute("DELETE FROM memberships WHERE user_sub=%s", (foreign_subject,))
            cur.execute("DELETE FROM users WHERE sub=%s", (foreign_subject,))


def test_congregation_member_reads_distributed_district_slot(owner, data, duty_rows):
    ids, other_subject, _ = duty_rows
    subject = data.sub(f"duty-congregation-{uuid.uuid4().hex[:8]}")
    slot_id = uuid.uuid4()
    assignment_id = uuid.uuid4()
    other_assignment_id = uuid.uuid4()
    with owner.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id,sub,email,username,is_superadmin,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,false,now(),now())",
            (str(uuid.uuid4()), subject, f"{subject}@example.org", subject),
        )
        cur.execute(
            "INSERT INTO memberships (id,user_sub,role,scope_type,scope_id,created_at,updated_at) "
            "VALUES (%s,%s,'VIEWER','CONGREGATION',%s,now(),now())",
            (str(uuid.uuid4()), subject, str(data.a.congregation_id)),
        )
        cur.execute(
            "INSERT INTO planning_slots "
            "(id,district_id,congregation_id,category,planning_date,planning_time,status,"
            "applicability,created_at,updated_at) VALUES "
            "(%s,%s,NULL,'Gottesdienst','2027-03-02','10:00','ACTIVE',%s,now(),now())",
            (
                str(slot_id),
                str(data.a.district_id),
                [str(data.a.congregation_id)],
            ),
        )
        cur.execute(
            "INSERT INTO event_duty_assignments "
            "(id,planning_slot_id,duty_category_id,district_id,congregation_id,display_name,"
            "duty_label,linked_user_sub,normalized_name,suggestion_id) "
            "VALUES (%s,%s,%s,%s,NULL,%s,'Testdienst',%s,NULL,NULL),"
            "(%s,%s,%s,%s,NULL,%s,'Testdienst',%s,NULL,NULL)",
            (
                str(assignment_id),
                str(slot_id),
                str(ids["category_a"]),
                str(data.a.district_id),
                subject,
                subject,
                str(other_assignment_id),
                str(slot_id),
                str(ids["category_a"]),
                str(data.a.district_id),
                other_subject,
                other_subject,
            ),
        )
    try:
        with app_session(subject) as cur:
            assert _visible_ids(
                cur,
                "planning_slots",
                [slot_id, ids["slot_b"]],
            ) == {slot_id}
            assert _visible_ids(
                cur,
                "event_duty_assignments",
                [assignment_id, other_assignment_id, ids["assignment_b"]],
            ) == {assignment_id}
    finally:
        with owner.cursor() as cur:
            cur.execute(
                "DELETE FROM event_duty_assignments WHERE id=ANY(%s::uuid[])",
                ([str(assignment_id), str(other_assignment_id)],),
            )
            cur.execute("DELETE FROM planning_slots WHERE id=%s", (str(slot_id),))
            cur.execute("DELETE FROM memberships WHERE user_sub=%s", (subject,))
            cur.execute("DELETE FROM users WHERE sub=%s", (subject,))


def test_subject_feed_is_restrictive_and_membership_aware(owner, duty_rows):
    ids, subject, token = duty_rows
    with export_session(token) as cur:
        assert _visible_ids(cur, "planning_slots", [ids["slot_a"], ids["slot_b"]]) == {
            ids["slot_a"]
        }
        assert _visible_ids(
            cur,
            "event_duty_assignments",
            [ids["assignment_a"], ids["assignment_b"]],
        ) == {ids["assignment_a"]}
    with owner.cursor() as cur:
        cur.execute("DELETE FROM memberships WHERE user_sub=%s", (subject,))
    with export_session(token) as cur:
        assert _visible_ids(cur, "planning_slots", [ids["slot_a"], ids["slot_b"]]) == set()
        assert (
            _visible_ids(
                cur,
                "event_duty_assignments",
                [ids["assignment_a"], ids["assignment_b"]],
            )
            == set()
        )
    with app_session(subject) as cur:
        cur.execute("DELETE FROM export_tokens WHERE id=%s", (str(ids["token"]),))
        assert cur.rowcount == 1


@pytest.fixture
async def capacity_tenant():
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    ids = {name: uuid.uuid4() for name in ("district", "congregation", "slot", "category")}
    subject = f"duty-capacity-{uuid.uuid4().hex}"
    async with sessions() as db:
        await db.execute(
            text(
                "INSERT INTO districts (id,name,created_at,updated_at) VALUES (:id,'D',now(),now())"
            ),
            {"id": ids["district"]},
        )
        await db.execute(
            text(
                "INSERT INTO congregations (id,name,district_id,created_at,updated_at) "
                "VALUES (:id,'G',:district,now(),now())"
            ),
            {"id": ids["congregation"], "district": ids["district"]},
        )
        await db.execute(
            text(
                "INSERT INTO planning_slots "
                "(id,district_id,congregation_id,category,planning_date,planning_time,status,"
                "applicability,created_at,updated_at) VALUES "
                "(:slot,:district,:congregation,'Gottesdienst','2027-04-01','10:00','ACTIVE',"
                "'{}',now(),now())"
            ),
            ids,
        )
        await db.execute(
            text(
                "INSERT INTO event_duty_categories "
                "(id,district_id,congregation_id,code,label,event_categories,enabled,capacity) "
                "VALUES (:id,:district,NULL,'capacity-test','Kapazität','{}',true,1)"
            ),
            {"id": ids["category"], "district": ids["district"]},
        )
        await db.execute(
            text(
                "INSERT INTO users (id,sub,email,username,is_superadmin,created_at,updated_at) "
                "VALUES (:id,:sub,:email,:sub,false,now(),now())"
            ),
            {"id": uuid.uuid4(), "sub": subject, "email": f"{subject}@example.org"},
        )
        await db.execute(
            text(
                "INSERT INTO memberships (id,user_sub,role,scope_type,scope_id,created_at,updated_at) "
                "VALUES (:id,:sub,'PLANNER','DISTRICT',:district,now(),now())"
            ),
            {"id": uuid.uuid4(), "sub": subject, "district": ids["district"]},
        )
        await db.commit()
    yield sessions, ids, subject
    async with sessions() as db:
        await db.execute(text("DELETE FROM districts WHERE id=:id"), {"id": ids["district"]})
        await db.execute(text("DELETE FROM memberships WHERE user_sub=:sub"), {"sub": subject})
        await db.execute(text("DELETE FROM users WHERE sub=:sub"), {"sub": subject})
        await db.commit()
    await engine.dispose()


async def _assign(sessions, ids, subject, name):
    db = sessions()
    try:
        await db.execute(
            text("SELECT set_config('app.current_user_sub', :sub, true)"),
            {"sub": subject},
        )
        assignment = await EventDutiesService(SqlEventDutiesRepository(db)).assign(
            ids["district"],
            ids["slot"],
            ids["category"],
            name=name,
        )
        return db, assignment
    except BaseException:
        await db.rollback()
        await db.close()
        raise


@pytest.mark.asyncio
async def test_concurrent_final_capacity_is_serialized(capacity_tenant):
    sessions, ids, subject = capacity_tenant
    first_db, first = await _assign(sessions, ids, subject, "Erste Person")
    competing = asyncio.create_task(_assign(sessions, ids, subject, "Zweite Person"))
    await asyncio.sleep(0.25)
    assert not competing.done(), "the competing writer must wait for the slot lock"
    await first_db.commit()
    await first_db.close()
    try:
        with pytest.raises(DutyConflictError):
            await competing
    finally:
        if competing.done() and not competing.cancelled() and competing.exception() is None:
            unexpected_db, _ = competing.result()
            await unexpected_db.rollback()
            await unexpected_db.close()

    async with sessions() as db:
        count = await db.scalar(
            text("SELECT count(*) FROM event_duty_assignments WHERE planning_slot_id=:slot"),
            {"slot": ids["slot"]},
        )
    assert first.display_name == "Erste Person"
    assert count == 1
