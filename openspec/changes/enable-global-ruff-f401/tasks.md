## Implementation checklist
- [x] Remove global Ruff F401 ignore and record RED CI: 87 errors.
- [x] Keep 32 ORM class registrations and one Alembic registry import explicitly documented.
- [x] Remove 54 diagnosed unused imports from app, migrations and tests.
- [x] Preserve the import-based calendar-router patch target after failing unit regression.
- [x] Remove redundant incremental CI check; add positive/negative Ruff and ORM metadata tests.
- [ ] Pass full backend Ruff, unit and PostgreSQL RLS suites; coverage >80%.
- [ ] Validate OpenSpec, Docker/Restore, security and front-end CI; remediate independent blockers.
- [ ] Obtain independent Codex review, merge and confirm green main.
