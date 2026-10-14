# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Tenant isolation enforced by PostgreSQL row-level security (real database).

These tests connect as the NOBYPASSRLS application role and set the same GUCs
the application sets per transaction (``app.current_user_sub``,
``app.is_system_worker``). They are skipped unless a migrated database is
configured:

    RLS_TEST_DATABASE_URL   owner/superuser DSN used to seed fixtures,
                            e.g. postgresql://nak:changeme@localhost:5432/nak_rls
    RLS_TEST_APP_PASSWORD   password of the application role (APP_DB_PASSWORD
                            during ``alembic upgrade``)
    APP_DB_USER             application role name (default: nak_app)
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import pytest

psycopg2 = pytest.importorskip("psycopg2")
from psycopg2 import errors  # noqa: E402
from psycopg2.extensions import make_dsn, parse_dsn  # noqa: E402

OWNER_DSN = os.getenv("RLS_TEST_DATABASE_URL")
APP_PASSWORD = os.getenv("RLS_TEST_APP_PASSWORD")
APP_ROLE = os.getenv("APP_DB_USER", "nak_app")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not (OWNER_DSN and APP_PASSWORD),
        reason="RLS_TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
    ),
]

# Tables carrying tenant keys that are intentionally governed by application
# checks instead of RLS (see openspec/changes/improve-tenant-isolation/tasks.md).
RLS_EXEMPT_TABLES = {
    "districts": "Root-Tenant; Zugriff über Membership-Prüfung (TenantValidationService)",
    "congregations": "Stammdaten des Bezirks; Zugriff über Membership-Prüfung",
}
TENANT_KEY_COLUMNS = ("district_id", "congregation_id", "leader_id", "planning_slot_id")
_CLEANUP_ORDER = (
    "external_event_candidates",
    "calendar_integrations",
    "leaders",
    "planning_slots",
    "congregations",
)


@dataclass(frozen=True)
class Tenant:
    district_id: uuid.UUID
    congregation_id: uuid.UUID
    slot_id: uuid.UUID
    leader_id: uuid.UUID
    unavailability_id: uuid.UUID
    integration_id: uuid.UUID
    candidate_id: uuid.UUID


@dataclass(frozen=True)
class Fixture:
    a: Tenant
    b: Tenant
    run: str

    def sub(self, name: str) -> str:
        return f"rls-{self.run}-{name}"


def _tenant() -> Tenant:
    return Tenant(*(uuid.uuid4() for _ in range(7)))


def _seed_tenant(cur, tenant: Tenant, label: str) -> None:
    cur.execute(
        "INSERT INTO districts (id, name, created_at, updated_at) VALUES (%s, %s, now(), now())",
        (str(tenant.district_id), f"RLS {label}"),
    )
    cur.execute(
        "INSERT INTO congregations (id, name, district_id, created_at, updated_at) "
        "VALUES (%s, %s, %s, now(), now())",
        (str(tenant.congregation_id), f"Gemeinde {label}", str(tenant.district_id)),
    )
    cur.execute(
        "INSERT INTO planning_slots (id, district_id, planning_date, planning_time, status, "
        "created_at, updated_at) VALUES (%s, %s, '2026-12-24', '18:00', 'ACTIVE', now(), now())",
        (str(tenant.slot_id), str(tenant.district_id)),
    )
    cur.execute(
        "INSERT INTO leaders (id, name, district_id) VALUES (%s, %s, %s)",
        (str(tenant.leader_id), f"Leiter {label}", str(tenant.district_id)),
    )
    cur.execute(
        "INSERT INTO leader_unavailabilities (id, leader_id, start_at, end_at, reason, "
        "created_at, updated_at) VALUES (%s, %s, '2026-12-01', '2026-12-02', 'Urlaub', now(), now())",
        (str(tenant.unavailability_id), str(tenant.leader_id)),
    )
    cur.execute(
        "INSERT INTO calendar_integrations (id, district_id, name, type, credentials_enc, "
        "created_at, updated_at, delete_behavior) "
        "VALUES (%s, %s, 'Feed', 'ICS', 'x', now(), now(), 'MARK_CANCELLED')",
        (str(tenant.integration_id), str(tenant.district_id)),
    )
    cur.execute(
        "INSERT INTO external_event_candidates (id, district_id, calendar_integration_id, "
        "external_event_id, source, title, start_at, end_at, content_hash, status, "
        "created_at, updated_at) VALUES (%s, %s, %s, 'uid', 'ICS', 'Konzert', "
        "'2026-12-24 18:00+00', '2026-12-24 19:00+00', 'hash', 'PENDING', now(), now())",
        (str(tenant.candidate_id), str(tenant.district_id), str(tenant.integration_id)),
    )


@pytest.fixture(scope="module")
def owner():
    connection = psycopg2.connect(OWNER_DSN)
    connection.autocommit = True
    yield connection
    connection.close()


@pytest.fixture(scope="module")
def data(owner) -> Iterator[Fixture]:
    fixture = Fixture(a=_tenant(), b=_tenant(), run=uuid.uuid4().hex[:8])
    memberships = [
        ("viewer-a", "VIEWER"),
        ("planner-a", "PLANNER"),
        ("admin-a", "DISTRICT_ADMIN"),
    ]
    with owner.cursor() as cur:
        _seed_tenant(cur, fixture.a, "A")
        _seed_tenant(cur, fixture.b, "B")
        for name in [*(m[0] for m in memberships), "superadmin", "outsider"]:
            cur.execute(
                "INSERT INTO users (id, sub, email, username, is_superadmin, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, now(), now())",
                (
                    str(uuid.uuid4()),
                    fixture.sub(name),
                    f"{fixture.sub(name)}@example.org",
                    fixture.sub(name),
                    name == "superadmin",
                ),
            )
        for name, role in memberships:
            cur.execute(
                "INSERT INTO memberships (id, user_sub, role, scope_type, scope_id, created_at, "
                "updated_at) VALUES (%s, %s, %s, 'DISTRICT', %s, now(), now())",
                (str(uuid.uuid4()), fixture.sub(name), role, str(fixture.a.district_id)),
            )
    yield fixture
    with owner.cursor() as cur:
        cur.execute("DELETE FROM memberships WHERE user_sub LIKE %s", (f"rls-{fixture.run}-%",))
        cur.execute("DELETE FROM users WHERE sub LIKE %s", (f"rls-{fixture.run}-%",))
        district_ids = [str(fixture.a.district_id), str(fixture.b.district_id)]
        for table in _CLEANUP_ORDER:  # children first; leaders cascade to unavailabilities
            cur.execute(
                f"DELETE FROM {table} WHERE district_id = ANY(%s::uuid[])",  # noqa: S608
                (district_ids,),
            )
        cur.execute("DELETE FROM districts WHERE id = ANY(%s::uuid[])", (district_ids,))


@contextmanager
def app_session(user_sub: str | None = None, *, system_worker: bool = False):
    """Transaction of the application role with request GUCs; always rolled back."""
    dsn = make_dsn(OWNER_DSN, user=APP_ROLE, password=APP_PASSWORD)
    connection = psycopg2.connect(dsn)
    try:
        with connection.cursor() as cur:
            if user_sub is not None:
                cur.execute("SELECT set_config('app.current_user_sub', %s, true)", (user_sub,))
            if system_worker:
                cur.execute("SELECT set_config('app.is_system_worker', 'true', true)")
            yield cur
    finally:
        connection.rollback()
        connection.close()


def _visible_ids(cur, table: str, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    cur.execute(f"SELECT id FROM {table} WHERE id = ANY(%s::uuid[])", ([str(i) for i in ids],))  # noqa: S608
    return {uuid.UUID(str(row[0])) for row in cur.fetchall()}


# ── Structural guarantees ────────────────────────────────────────────────────


def test_application_role_cannot_bypass_rls(owner) -> None:
    with owner.cursor() as cur:
        cur.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s", (APP_ROLE,))
        assert cur.fetchone() == (False, False)


def test_every_tenant_table_has_rls_enabled(owner) -> None:
    with owner.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT c.relname, c.relrowsecurity
            FROM pg_class c
            JOIN information_schema.columns col
              ON col.table_name = c.relname AND col.table_schema = 'public'
            WHERE c.relnamespace = 'public'::regnamespace
              AND c.relkind = 'r'
              AND col.column_name = ANY(%s)
            """,
            (list(TENANT_KEY_COLUMNS),),
        )
        without_rls = sorted(
            table
            for table, enabled in cur.fetchall()
            if not enabled and table not in RLS_EXEMPT_TABLES
        )
    assert without_rls == [], f"Tenant tables without row-level security: {without_rls}"


# ── Planning slots: read isolation ───────────────────────────────────────────


def test_member_sees_only_own_district(data) -> None:
    with app_session(data.sub("viewer-a")) as cur:
        assert _visible_ids(cur, "planning_slots", [data.a.slot_id, data.b.slot_id]) == {
            data.a.slot_id
        }


@pytest.mark.parametrize("user", [None, "outsider"], ids=["no-identity", "no-membership"])
def test_missing_identity_or_membership_sees_nothing(data, user) -> None:
    sub = data.sub(user) if user else None
    with app_session(sub) as cur:
        assert _visible_ids(cur, "planning_slots", [data.a.slot_id, data.b.slot_id]) == set()


def test_forged_subject_without_user_row_sees_nothing(data) -> None:
    with app_session(f"forged-{uuid.uuid4()}") as cur:
        assert _visible_ids(cur, "planning_slots", [data.a.slot_id, data.b.slot_id]) == set()


def test_superadmin_bypass_sees_all_districts(data) -> None:
    with app_session(data.sub("superadmin")) as cur:
        assert _visible_ids(cur, "planning_slots", [data.a.slot_id, data.b.slot_id]) == {
            data.a.slot_id,
            data.b.slot_id,
        }


def test_system_worker_sees_all_districts(data) -> None:
    with app_session(system_worker=True) as cur:
        assert _visible_ids(cur, "planning_slots", [data.a.slot_id, data.b.slot_id]) == {
            data.a.slot_id,
            data.b.slot_id,
        }


# ── Planning slots: write isolation ──────────────────────────────────────────

_INSERT_SLOT = (
    "INSERT INTO planning_slots (id, district_id, planning_date, planning_time, status, "
    "created_at, updated_at) VALUES (%s, %s, '2027-01-01', '10:00', 'ACTIVE', now(), now())"
)


def test_planner_can_write_in_own_district(data) -> None:
    with app_session(data.sub("planner-a")) as cur:
        cur.execute(_INSERT_SLOT, (str(uuid.uuid4()), str(data.a.district_id)))
        assert cur.rowcount == 1


@pytest.mark.parametrize(
    ("user", "district"),
    [("viewer-a", "a"), ("planner-a", "b")],
    ids=["viewer-own-district", "planner-foreign-district"],
)
def test_insert_without_write_permission_is_rejected(data, user, district) -> None:
    target = getattr(data, district).district_id
    with app_session(data.sub(user)) as cur, pytest.raises(errors.InsufficientPrivilege):
        cur.execute(_INSERT_SLOT, (str(uuid.uuid4()), str(target)))


def test_update_and_delete_of_foreign_rows_affect_nothing(data) -> None:
    with app_session(data.sub("planner-a")) as cur:
        cur.execute(
            "UPDATE planning_slots SET status = 'CANCELLED' WHERE id = %s", (str(data.b.slot_id),)
        )
        assert cur.rowcount == 0
        cur.execute("DELETE FROM planning_slots WHERE id = %s", (str(data.b.slot_id),))
        assert cur.rowcount == 0


def test_planner_cannot_move_own_row_into_foreign_district(data) -> None:
    with app_session(data.sub("planner-a")) as cur, pytest.raises(errors.InsufficientPrivilege):
        cur.execute(
            "UPDATE planning_slots SET district_id = %s WHERE id = %s",
            (str(data.b.district_id), str(data.a.slot_id)),
        )


# ── External event candidates (0022) ────────────────────────────────────────


def test_candidates_visible_to_own_district_admin_only(data) -> None:
    ids = [data.a.candidate_id, data.b.candidate_id]
    with app_session(data.sub("admin-a")) as cur:
        assert _visible_ids(cur, "external_event_candidates", ids) == {data.a.candidate_id}
    with app_session(data.sub("viewer-a")) as cur:
        assert _visible_ids(cur, "external_event_candidates", ids) == set()


def test_candidate_review_in_foreign_district_affects_nothing(data) -> None:
    with app_session(data.sub("admin-a")) as cur:
        cur.execute(
            "UPDATE external_event_candidates SET status = 'DISMISSED' WHERE id = %s",
            (str(data.b.candidate_id),),
        )
        assert cur.rowcount == 0


def test_system_worker_can_ingest_candidates(data) -> None:
    with app_session(system_worker=True) as cur:
        cur.execute(
            "INSERT INTO external_event_candidates (id, district_id, calendar_integration_id, "
            "external_event_id, source, title, start_at, end_at, content_hash, status, "
            "created_at, updated_at) VALUES (%s, %s, %s, 'uid-2', 'ICS', 'Neu', "
            "'2026-12-25 18:00+00', '2026-12-25 19:00+00', 'hash', 'PENDING', now(), now())",
            (str(uuid.uuid4()), str(data.b.district_id), str(data.b.integration_id)),
        )
        assert cur.rowcount == 1


# ── Leader unavailabilities (0022) ───────────────────────────────────────────

_INSERT_UNAVAILABILITY = (
    "INSERT INTO leader_unavailabilities (id, leader_id, start_at, end_at, reason, created_at, "
    "updated_at) VALUES (%s, %s, '2027-02-01', '2027-02-02', 'Krank', now(), now())"
)


def test_unavailabilities_follow_leader_visibility(data) -> None:
    ids = [data.a.unavailability_id, data.b.unavailability_id]
    with app_session(data.sub("viewer-a")) as cur:
        assert _visible_ids(cur, "leader_unavailabilities", ids) == {data.a.unavailability_id}


def test_planner_records_unavailability_in_own_district(data) -> None:
    with app_session(data.sub("planner-a")) as cur:
        cur.execute(_INSERT_UNAVAILABILITY, (str(uuid.uuid4()), str(data.a.leader_id)))
        assert cur.rowcount == 1


@pytest.mark.parametrize(
    ("user", "leader"),
    [("viewer-a", "a"), ("planner-a", "b")],
    ids=["viewer-own-district", "planner-foreign-leader"],
)
def test_unavailability_write_without_permission_is_rejected(data, user, leader) -> None:
    leader_id = getattr(data, leader).leader_id
    with app_session(data.sub(user)) as cur, pytest.raises(errors.InsufficientPrivilege):
        cur.execute(_INSERT_UNAVAILABILITY, (str(uuid.uuid4()), str(leader_id)))


def test_owner_dsn_is_parseable() -> None:
    """Guard against misconfiguration producing confusing connection errors."""
    assert parse_dsn(OWNER_DSN)["dbname"]
