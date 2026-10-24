## Why
Issue #715 requires removing Ruff's global F401 suppression. Six staged PRs (#719–#726) only protected selected backend modules; migrations, tests, DB adapters and API routers remained unprotected.

## What Changes
- Remove `F401` from backend global ignores; enforce it using the existing pinned `uv run ruff check .` quality gate for all Python modules.
- Delete the redundant incremental F401 CI step.
- Resolve 87 lint diagnostics from [RED CI 40108440503](https://github.com/stritti/nak-district-planner/actions/runs/40108440503): keep 32 ORM registration/re-exports using explicit `__all__`, keep one Alembic registration import as explicit alias, remove 54 truly unused imports.
- Preserve the runtime `encrypt_credentials` compatibility import in the calendar router as an explicit alias (a regression test patches that symbol).
- Add positive/negative Ruff fixtures and ORM registration tests.

## Capabilities
### Modified Capabilities
- `ci-quality-gates`: project-wide Python F401 enforcement and intentional re-export safety.

## Impact
Lint config, imports in backend/migrations/tests, OpenSpec, CI and tests. No intended business logic or API contract changes.
