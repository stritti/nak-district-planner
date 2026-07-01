---
name: alembic-migrations
description: Use when creating, reviewing, or fixing Alembic database migrations. Covers revision chain management, multi-head avoidance, merge migrations, PostgreSQL identifier length limits, and CI checks. Also use when debugging "Multiple head revisions" errors or FK name length failures.
---

# Alembic Migration Conventions

This project uses Alembic with async SQLAlchemy 2.0 + PostgreSQL 15+.

## Revision Chain Rules

### Heads: Exactly One

The migration chain MUST have exactly one head at all times. Multiple heads
break `alembic upgrade head` and block CI/CD.

```bash
# Check locally
alembic heads
# Expected output: <revision> (head)  — exactly one line
```

### When Branching Is Necessary

If you must create a migration from a non-tip revision (e.g., backporting a
hotfix to an older state), you MUST also create a **merge migration**
immediately afterward.

**Merge migration template:**

```python
"""merge <description>

Revision ID: ae6c055cc0XX
Revises: <rev1>, <rev2>
Create Date: 2026-06-29 12:00:00.000000
"""
from __future__ import annotations
from collections.abc import Sequence

revision: str = "ae6c055cc0XX"
down_revision: str | None = ("<rev1>", "<rev2>")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
```

**Existing merge examples in the project:**
- `ae6c055cc050_merge_heads.py` — merges `0010_leader_registrations` and `4c9a2d7e8f10`
- `ed967c737376_merge_planning_model_with_main_chain.py` — merges `0011_planning_model_foundation` and `e4b2a9d7f110`
- `ae6c055cc051_merge_0125_with_0012.py` — 3-way merge of `0012`, `0125_remove_events_add_sync_fields`, and `e5a2b3c4d5f0`

### Dependency Ordering: Respect Table Creation Order

`down_revision` determines when a migration runs in the topological order.
If your migration references a table, the `down_revision` chain MUST include
the migration that **creates** that table as an ancestor.

**Bad — references table that doesn't exist yet:**
```python
# 0123_matrix_migration_add_planning_slot_fields.py
down_revision = "faecec299731"   # ← branches BEFORE planning_slots was created

def upgrade():
    op.add_column("planning_slots", ...)   # ❌ relation "planning_slots" does not exist
```

**Good — chain includes the table-creating migration:**
```python
# 0123_matrix_migration_add_planning_slot_fields.py (fixed)
down_revision = "ed967c737376"   # ← merge that brought planning_slots into main chain

def upgrade():
    op.add_column("planning_slots", ...)   # ✅ table exists
```

**Rule of thumb:** If you reference a table or column that was added in a
migration from a different branch, anchor your migration at or after the
**merge point** that brought that feature in, not at a revision before it.

To find where a table was created:
```bash
grep -l "create_table('your_table'" alembic/versions/*.py
```

### Naming Convention

Migration filenames: `<revision>_<short_description>.py`

- Use sequential 4-digit prefixes for main-chain migrations (`0001_`, `0002_`, ..., `0012_`)
- Use 4-hex-digit or random-looking IDs for branch or ad-hoc migrations (`ae6c055cc050`, `e5a2b3c4d5f0`)
- Merge migrations: `<revision>_merge_<description>.py`

## Revision ID Length Limit

Alembic stores the current revision in a `VARCHAR(32)` column. Revision IDs
must be **32 characters or fewer** — otherwise `alembic upgrade head` fails
with `value too long for type character varying(32)`.

**Bad — 46 characters:**
```python
revision = "0123_matrix_migration_add_planning_slot_fields"  # ❌
```

**Good — 4 digits:**
```python
revision = "0123"  # ✅
```

This applies to the `revision` field in the migration file AND to its
references in `down_revision` of dependent migrations and merge migrations.

## PostgreSQL FK Name Limit

PostgreSQL limits identifiers (including constraint names) to **63 characters**.

An FK name following the convention
`fk_<source_table>_<local_column>_<target_table>` can easily exceed this.

**Bad — 64 characters:**
```python
op.create_foreign_key(
    "fk_planning_slots_invitation_source_congregation_id_congregations",
    ...
)
```

**Good — 55 characters:**
```python
op.create_foreign_key(
    "fk_planning_slots_inv_src_congregation_id_congregations",
    ...
)
```

**Check locally:**
```bash
# Find all FK names in migration files with length >= 60 (safety buffer)
python3 -c "
import re, sys
for f in sys.argv[1:]:
    with open(f) as fh:
        for i, line in enumerate(fh, 1):
            m = re.search(r'\"(fk_\w{50,})\"', line)
            if m:
                name = m.group(1)
                if len(name) > 55:
                    print(f'{f}:{i}: {name} ({len(name)} chars)')
" alembic/versions/*.py
```

**Always count before writing FK names:**
```bash
echo -n "fk_your_table_your_column_referenced_table" | wc -c
```

## Verification Checklist

Before committing migration changes:

- [ ] `alembic heads` shows exactly one `(head)` line
- [ ] `alembic upgrade head --sql` exits with code 0
- [ ] No FK constraint name exceeds 63 characters (grep for `fk_` names)
- [ ] `downgrade()` function is implemented (mirrors upgrade)
- [ ] Migration applies cleanly on a fresh database (`alembic upgrade head`)

## CI

A GitHub Actions workflow (`.github/workflows/alembic-check.yml`) runs
automatically on every PR to verify head count, FK name lengths, and offline
SQL generation.
