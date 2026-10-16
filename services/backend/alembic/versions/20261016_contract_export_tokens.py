# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Hash-only contract for bearer-style ICS export tokens (#602).

The historical migrations stay frozen: they must run before the nullable
token_hash column exists. Upgrade replaces their active SQL definitions before
dropping plaintext. This is intentionally a one-way contract migration;
plaintext credentials cannot be recovered from SHA-256 hashes on downgrade.
"""

from __future__ import annotations

import re

import sqlalchemy as sa
from alembic import op

from app.adapters.db.migrations.event_duty_rls import (
    _FUNCTIONS,
    _subject_leader_read,
    _subject_slot_read,
)
from app.adapters.db.migrations.rls_policies import (
    export_token_lookup_sql,
    related_planning_slot_sql,
)

revision = "20261016_contract_export_tokens"
down_revision = "20261015_hash_export_tokens"
branch_labels = None
depends_on = None

_TOKEN_REFERENCE = re.compile(
    r"(?P<alias>et|export_tokens)\.token\s*=\s*"
    r"current_setting\(\s*'app\.current_export_token'\s*,\s*true\s*\)",
    flags=re.IGNORECASE,
)


def _convert_legacy_sql(sql: str) -> str:
    """Replace only the known, bounded legacy RLS bearer-token predicates."""
    converted, matches = _TOKEN_REFERENCE.subn(
        lambda match: (
            f"{match.group('alias')}.token_hash = "
            "encode(sha256(current_setting('app.current_export_token', true)::bytea), 'hex')"
        ),
        sql,
    )
    if "app.current_export_token" in sql and not matches:
        raise RuntimeError("Unrecognized legacy export-token SQL: refusing contract migration")
    return converted


def _select_policies() -> tuple[tuple[str, str, str], ...]:
    return (
        (
            "planning_slots", "planning_slots_tenant_isolation_policy",
            _subject_slot_read("planning_slots"),
        ),
        (
            "event_instances", "event_instances_tenant_isolation_policy",
            related_planning_slot_sql("event_instances", _subject_slot_read),
        ),
        (
            "service_assignments", "service_assignments_tenant_isolation_policy",
            related_planning_slot_sql(
                "service_assignments",
                lambda alias: _subject_slot_read(alias, "service_assignments"),
            ),
        ),
        ("leaders", "leaders_tenant_isolation_policy", _subject_leader_read()),
        ("export_tokens", "export_tokens_select_policy", export_token_lookup_sql()),
    )


def upgrade() -> None:
    # Validate all old and mixed-version writes before cutting the plaintext away.
    op.execute(
        "UPDATE export_tokens SET token_hash=encode(sha256(token::bytea), 'hex') "
        "WHERE token_hash IS NULL"
    )
    connection = op.get_bind()
    mismatches = connection.execute(sa.text(
        "SELECT count(*) FROM export_tokens "
        "WHERE token_hash IS DISTINCT FROM encode(sha256(token::bytea), 'hex')"
    )).scalar_one()
    if mismatches:
        raise RuntimeError(
            f"Export token contract rejected {mismatches} mismatching hashes"
        )

    # Overwrite only the three export functions and personal_calendar_scopes.
    # CREATE OR REPLACE keeps their fixed SECURITY DEFINER search_path/grants.
    for definition in _FUNCTIONS:
        if "app.current_export_token" not in definition:
            continue
        converted = _convert_legacy_sql(definition)
        op.execute(converted.replace("CREATE FUNCTION ", "CREATE OR REPLACE FUNCTION ", 1))

    # Recreate *active* policies installed by the duties migration, including
    # all derivations of planning_slots and the export_tokens select policy.
    # Dropping/recreating policies is transactional in PostgreSQL.
    for table, policy, using in _select_policies():
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
        op.execute(
            f"CREATE POLICY {policy} ON {table} "
            f"FOR SELECT USING {_convert_legacy_sql(using)}"
        )

    op.alter_column(
        "export_tokens", "token_hash",
        existing_type=sa.String(64), nullable=False,
    )
    # Default RESTRICT rejects any undiscovered SQL dependency on token.
    op.drop_column("export_tokens", "token")


def downgrade() -> None:
    raise RuntimeError(
        "Irreversible hash-only contract: restore pre-contract backup and rotate "
        "subscriptions if rollback is required; plaintext cannot be derived from SHA-256"
    )
