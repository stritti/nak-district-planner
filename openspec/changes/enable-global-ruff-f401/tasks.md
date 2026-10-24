## Implementation checklist
- [x] Remove global Ruff F401 ignore and record RED CI: 87 errors.
- [x] Keep 32 ORM class registrations and one Alembic registry import explicitly documented.
- [x] Remove 54 diagnosed unused imports from app, migrations and tests.
- [x] Preserve the calendar-router patch target as an explicit module attribute, and address the later CodeQL unused-import review finding without suppressing it.
- [x] Remove redundant incremental CI check; add positive/negative Ruff and ORM metadata tests.
- [x] Pass full backend Ruff, unit and PostgreSQL RLS suites; coverage >80%.
- [x] Validate OpenSpec, Docker/Restore, security and front-end CI; remediate independent blockers.
- [x] Obtain independent Codex review, merge and confirm green main.

## Verification evidence
- Pull request #741 was merged as `61c2ddcc157239e6957c064749338c1058da5e70` after all 9 relevant PR workflows succeeded and Codex reviewed the final head without findings.
- Post-merge `main` CI [run 40128985498](https://github.com/stritti/nak-district-planner/actions/runs/40128985498) passed Ruff, PostgreSQL RLS integration/performance and unit tests, with coverage threshold and critical-router checks successful.
- The post-merge Security Scans, MegaLinter, Docker validation, Restore Drill, Alembic, docs/OpenSpec and frontend workflows all succeeded on the same merge SHA.
- Repository-wide Ruff F401 is enabled in `services/backend/pyproject.toml`; no global ignore or redundant isolated gate remains. The issue #715 remediation is complete.
