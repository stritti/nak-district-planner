# Final Ruff F401 cleanup (#715)

**Goal:** Switch to repository-wide Ruff F401 without breaking SQLAlchemy, Alembic, or FastAPI integration and test compatibility.

**Process:** TDD Red-Green, Clean Code, OpenSpec, independent code review, CI verification with coverage >80%.

## Steps
1. [x] RED: run 40108440503 exposed 87 F401 violations in 35 files.
2. [x] Preserve 32 ORM imports as explicit `__all__` exports and one Alembic side-effect import.
3. [x] Remove 54 unused symbols; keep calendar router compatibility patch target via redundant alias.
4. [x] Remove global F401 suppression and redundant isolated CI step; add positive/negative tests and ORM metadata test.
5. [x] GREEN: complete lint and unit/PG-RLS integration tests with >80% coverage.
6. [x] Validate Docker build / restore against the current main baseline and resolve blockers.
7. [x] Codex review, merge PR, validate main and close issue #715.

## Risks
- Never remove ORM imports required for SQLAlchemy metadata registration.
- Preserve runtime patch-target exports even if Ruff cannot see dynamic usage.
- Don't add blanket F401 ignores, disable security workflows or weaken coverage.
- Avoid unrelated behavior changes; isolate infrastructure regressions.

## Completion evidence
- Post-merge full CI on `main` at `61c2ddc`: [CI #40128985498](https://github.com/stritti/nak-district-planner/actions/runs/40128985498), plus Security Scans, MegaLinter, Docker, docs/OpenSpec, Restore Drill and Alembic workflows all successful.
- Backend coverage threshold >80% and critical-router thresholds >=80% passed; independent Codex review for PR #741 has no unresolved findings.
