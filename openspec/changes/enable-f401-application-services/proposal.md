## Why
Issue #715 progressively restores Ruff F401 checks across the backend. PRs #719, #720 and #721 already cover the registration router, all domain models, domain ports, planning and domain services. Application workflows (30 Python modules) are not yet protected by the isolated F401 quality gate.

## What Changes
- Include the entire `app/application` tree in the existing CI Ruff `--isolated --select F401` check.
- Remove five genuinely unused imports diagnosed by the negative CI run: one `Optional` in CSRF service, four stale imports in the holiday service (following its earlier migration from Events to PlanningSlots).
- Keep all previously enforced paths, domain package exports, and the global F401 ignore until adapter/test modules have been audited.

## Capabilities
### Modified Capabilities
- `ci-quality-gates`: protect application service imports.

## Impact
Workflow and import-only modifications to application services; OpenSpec and implementation plan. No API, database, migration or functional changes.
