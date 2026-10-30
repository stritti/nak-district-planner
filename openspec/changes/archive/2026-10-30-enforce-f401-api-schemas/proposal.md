## Why
Issue #715 is incrementally restoring the Ruff F401 unused-import gate. The domain packages, application services, identity/mail/calendar/worker adapters and registrations router are already covered by merged PRs #719–#724. API Pydantic schemas remain globally ignored.

## What Changes
- Add the entire `app/adapters/api/schemas` directory (17 Python modules) to the preexisting isolated Ruff `F401` check.
- Preserve all already-checked modules (including `app/application`) without weakening the global CI checks.
- No unused imports were reported in the new directory, therefore no Pydantic model or application code changes are necessary.
- Keep the global F401 ignore pending the remaining router/database/test audits.

## Capabilities
### Modified Capabilities
- `ci-quality-gates`: check all current and future API schema imports with isolated F401.

## Impact
The GitHub Actions backend CI workflow, OpenSpec and implementation plan; **no** API contracts, model serialization, database or runtime behavior changes.
