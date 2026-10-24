## Red-Green evidence and classification
A CI-only change removed `"F401"` from `services/backend/pyproject.toml`, yielding 87 F401 errors on [run 40108440503](https://github.com/stritti/nak-district-planner/actions/runs/40108440503).
The 87 diagnostic locations were classified: 32 ORM classes are intentionally imported to register SQLAlchemy tables; one Alembic import performs registry initialization; 54 production/migration/test imports were genuinely unused.

## Decisions
- Activate F401 globally in pinned Ruff config. Eliminate the redundant isolated directory-specific CI check.
- Declare all 32 ORM exports explicitly in `app.adapters.db.orm_models.__all__`; Alembic imports ORM registry with a redundant alias to retain registration side effects. `Base.metadata` must still include each table.
- Remove only confirmed unused imports, without blanket `noqa: F401`.
- Preserve the calendar-router `encrypt_credentials` import as an explicit alias because an existing test and potential downstream code use it as a monkeypatch target. The first full unit run caught this compatibility requirement; correction is included.
- Add unit regression checks: F401 absent from global ignores; execute pinned Ruff with the repository configuration on a positive used-import fixture and negative unused-import fixture; verify ORM exports and table metadata.

## Verification
- Full `uv run ruff check .` and Alembic + backend PostgreSQL-RLS integration tests.
- All backend unit tests, including negative/error paths, critical-router coverage >=80%, global backend coverage >80%.
- Frontend E2E/unit tests, docs/OpenSpec, Security Scans and Docker/Restore workflows, followed by Codex review on final head.
- Docker image build may independently fail on current main's new Python 3.15 image because `httptools` lacks a compiled wheel and GCC is absent; do not downgrade or bypass quality gates. Track and fix any independent build regression separately before merge.
