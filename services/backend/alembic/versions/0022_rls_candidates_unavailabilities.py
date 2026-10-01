"""Enable RLS on external_event_candidates and leader_unavailabilities.

Both tables were added after the tenant-isolation baseline (0014) and hold
district-scoped data without row-level policies, so a session of the
NOBYPASSRLS application role could read and modify rows of every district.
The policies mirror the application guards:

- external_event_candidates: DISTRICT_ADMIN of the candidate's district
  (sync ingestion by the system worker is covered by the superadmin clause).
- leader_unavailabilities: visible when the leader row is visible (the leaders
  policy applies inside the subquery); writes require PLANNER or higher in the
  leader's district.

Revision ID: 0022
Revises: 0021
"""

from __future__ import annotations

from alembic import op
from app.adapters.db.migrations.rls_policies import (
    SUPERADMIN_SQL,
    district_admin_membership_sql,
    district_write_membership_sql,
)

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

_CANDIDATE_ACCESS = (
    f"({SUPERADMIN_SQL} OR {district_admin_membership_sql('external_event_candidates')})"
)
_UNAVAILABILITY_READ = (
    "EXISTS (SELECT 1 FROM leaders l WHERE l.id = leader_unavailabilities.leader_id)"
)
_UNAVAILABILITY_WRITE = f"""EXISTS (
    SELECT 1 FROM leaders l
    WHERE l.id = leader_unavailabilities.leader_id
      AND ({SUPERADMIN_SQL} OR {district_write_membership_sql("l")})
)"""

# nosec B608 — policy DDL with internal identifiers only, values via current_setting GUCs
_POLICIES: dict[str, dict[str, str]] = {
    "external_event_candidates": {
        "select": f"FOR SELECT USING {_CANDIDATE_ACCESS}",
        "insert": f"FOR INSERT WITH CHECK {_CANDIDATE_ACCESS}",
        "update": f"FOR UPDATE USING {_CANDIDATE_ACCESS} WITH CHECK {_CANDIDATE_ACCESS}",
        "delete": f"FOR DELETE USING {_CANDIDATE_ACCESS}",
    },
    "leader_unavailabilities": {
        "select": f"FOR SELECT USING ({_UNAVAILABILITY_READ})",
        "insert": f"FOR INSERT WITH CHECK ({_UNAVAILABILITY_WRITE})",
        "update": f"FOR UPDATE USING ({_UNAVAILABILITY_WRITE}) WITH CHECK ({_UNAVAILABILITY_WRITE})",
        "delete": f"FOR DELETE USING ({_UNAVAILABILITY_WRITE})",
    },
}


def upgrade() -> None:
    for table, policies in _POLICIES.items():
        # Policies first, then enable RLS: no window with RLS but no policy.
        for action, clause in policies.items():
            op.execute(f"CREATE POLICY {table}_{action}_policy ON {table} {clause}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table, policies in _POLICIES.items():
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        for action in policies:
            op.execute(f"DROP POLICY IF EXISTS {table}_{action}_policy ON {table}")
