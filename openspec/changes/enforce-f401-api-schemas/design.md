## Decision
Extend the existing `uv run ruff check --isolated --select F401` workflow step to cover all modules under `app/adapters/api/schemas`. A directory-level rule covers added schemas automatically. `--isolated` bypasses the existing repo-wide F401 ignore, which remains needed until other adapter/test modules are audited.

## Verification evidence
The initial CI-only commit `f05d7b7` triggered [GitHub Actions run 40098618093](https://github.com/stritti/nak-district-planner/actions/runs/40098618093). Ruff F401 passed on the full combined scope, including all 17 schemas; none of their imports required removal. For regression behavior on an unused import, issue #715 has RED CI runs 40086639329 and 40030528685 using this same isolated command. No production Pydantic imports are changed.

## Compatibility and error paths
Pydantic validation, forward references and FastAPI request/response schema imports remain identical. Existing backend unit, error-path, PostgreSQL RLS integration and router tests must pass. The backend coverage target remains strictly above 80%.

## Following stages
API routers/middleware and database ORM/repositories/migrations plus test modules have not been added by this PR. Audit them separately, guard intentional package reexports, then remove the global F401 ignore.
