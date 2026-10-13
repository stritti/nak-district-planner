# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""PostgreSQL regression tests for recurring event tenant RLS and durable links.

Use the restricted application role and the same per-request GUCs as production.
These tests are skipped without the migrated PostgreSQL test environment.
"""

from __future__ import annotations

import json
import uuid

import pytest

from tests.integration.test_rls_postgres import (
    APP_PASSWORD,
    OWNER_DSN,
    _visible_ids,
    app_session,
    data,
    owner,
    psycopg2,
)

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        not (OWNER_DSN and APP_PASSWORD),
        reason="RLS_TEST_DATABASE_URL / RLS_TEST_APP_PASSWORD not configured",
    ),
]

_RULE = json.dumps({
    "version": 1,
    "kind": "WEEKLY",
    "anchor_date": "2026-11-03",
    "interval": 1,
    "weekdays": [2],
    "day_of_month": None,
    "weekday": None,
    "ordinal": None,
})

_INSERT_TEMPLATE = (
    "INSERT INTO recurring_event_templates "
    "(id, district_id, congregation_id, title, category, start_time, duration_minutes, "
    "recurrence, applicability, excluded_dates, is_active, revision, timezone, "
    "created_at, updated_at) VALUES "
    "(%s, %s, %s, 'Chorprobe', 'Musik', '19:30', 90, %s::jsonb, "
    "'{}'::varchar[], '[]'::jsonb, true, 1, 'Europe/Berlin', now(), now())"
)


def _seed_template(cur, district_id, congregation_id=None):
    template_id = uuid.uuid4()
    cur.execute(
        _INSERT_TEMPLATE,
        (str(template_id), str(district_id),
         str(congregation_id) if congregation_id else None, _RULE),
    )
    return template_id


def _seed_decision(cur, template_id, district_id, *, slot_id=None):
    decision_id = uuid.uuid4()
    cur.execute(
        "INSERT INTO recurring_event_decisions "
        "(id, district_id, template_id, occurrence_local_date, status, planning_slot_id, "
        "created_by, created_at, updated_at) "
        "VALUES (%s, %s, %s, '2026-11-03', %s, %s, 'rls-test', now(), now())",
        (
            str(decision_id), str(district_id), str(template_id),
            "ACCEPTED" if slot_id else "SKIPPED",
            str(slot_id) if slot_id else None,
        ),
    )
    return decision_id


@pytest.fixture
def recurring_rows(owner, data):
    """Own disposable recurring rows in both seeded districts."""
    with owner.cursor() as cur:
        template_a = _seed_template(cur, data.a.district_id, data.a.congregation_id)
        template_b = _seed_template(cur, data.b.district_id, data.b.congregation_id)
        decision_a = _seed_decision(cur, template_a, data.a.district_id)
        decision_b = _seed_decision(cur, template_b, data.b.district_id)
    yield template_a, template_b, decision_a, decision_b
    with owner.cursor() as cur:
        cur.execute(
            "DELETE FROM recurring_event_templates WHERE id = ANY(%s::uuid[])",
            ([str(template_a), str(template_b)],),
        )


def test_recurring_rls_reader_sees_only_own_templates_and_decisions(data, recurring_rows):
    template_a, template_b, decision_a, decision_b = recurring_rows
    with app_session(data.sub("viewer-a")) as cur:
        assert _visible_ids(cur, "recurring_event_templates", [template_a, template_b]) == {
            template_a,
        }
        assert _visible_ids(cur, "recurring_event_decisions", [decision_a, decision_b]) == {
            decision_a,
        }
    with app_session(data.sub("outsider")) as cur:
        assert _visible_ids(cur, "recurring_event_templates", [template_a, template_b]) == set()
        assert _visible_ids(cur, "recurring_event_decisions", [decision_a, decision_b]) == set()
    with app_session(system_worker=True) as cur:
        assert _visible_ids(cur, "recurring_event_templates", [template_a, template_b]) == {
            template_a, template_b,
        }


def test_recurring_rls_blocks_viewer_mutations_and_foreign_admin_writes(data, recurring_rows):
    template_a, template_b, _, _ = recurring_rows
    with app_session(data.sub("viewer-a")) as cur:
        cur.execute(
            "UPDATE recurring_event_templates SET title = 'Unexpected' WHERE id = %s",
            (str(template_a),),
        )
        assert cur.rowcount == 0
    with app_session(data.sub("admin-a")) as cur:
        cur.execute(
            "UPDATE recurring_event_templates SET title = 'Foreign' WHERE id = %s",
            (str(template_b),),
        )
        assert cur.rowcount == 0
        cur.execute(
            "UPDATE recurring_event_templates SET title = 'Own' WHERE id = %s",
            (str(template_a),),
        )
        assert cur.rowcount == 1


def test_recurring_decisions_survive_slot_retention_deletion(owner, data):
    slot_id = uuid.uuid4()
    with owner.cursor() as cur:
        template_id = _seed_template(cur, data.a.district_id, data.a.congregation_id)
        cur.execute(
            "INSERT INTO planning_slots "
            "(id, district_id, congregation_id, planning_date, planning_time, status, "
            "created_at, updated_at) VALUES "
            "(%s, %s, %s, '2026-11-03', '18:30', 'ACTIVE', now(), now())",
            (str(slot_id), str(data.a.district_id), str(data.a.congregation_id)),
        )
        decision_id = _seed_decision(
            cur, template_id, data.a.district_id, slot_id=slot_id,
        )
    try:
        with owner.cursor() as cur:
            cur.execute("DELETE FROM planning_slots WHERE id = %s", (str(slot_id),))
            cur.execute(
                "SELECT status, planning_slot_id FROM recurring_event_decisions WHERE id = %s",
                (str(decision_id),),
            )
            assert cur.fetchone() == ("ACCEPTED", None)
        with app_session(data.sub("viewer-a")) as cur:
            assert _visible_ids(cur, "recurring_event_decisions", [decision_id]) == {
                decision_id,
            }
    finally:
        with owner.cursor() as cur:
            cur.execute(
                "DELETE FROM recurring_event_templates WHERE id = %s", (str(template_id),),
            )
            cur.execute("DELETE FROM planning_slots WHERE id = %s", (str(slot_id),))


def test_recurring_decision_rejects_foreign_district_slot(owner, data):
    with owner.cursor() as cur:
        template_id = _seed_template(cur, data.a.district_id)
    try:
        with owner.cursor() as cur:
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                _seed_decision(
                    cur, template_id, data.a.district_id, slot_id=data.b.slot_id,
                )
    finally:
        with owner.cursor() as cur:
            cur.execute(
                "DELETE FROM recurring_event_templates WHERE id = %s", (str(template_id),),
            )


def test_recurring_template_rejects_foreign_district_congregation(owner, data):
    with owner.cursor() as cur:
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            _seed_template(cur, data.a.district_id, data.b.congregation_id)
