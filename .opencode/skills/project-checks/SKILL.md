---
name: project-checks
description: Run project quality checks after code changes. Executes linting, type checking, and tests for both backend and frontend.
license: MIT
metadata:
  author: Claude
  version: "1.0"
---

Run project quality checks to verify code changes.

**Input**: None required. Checks both backend and frontend.

**Steps**

1. **Backend Checks (services/backend/)**

   Run these commands:
   - `uv run ruff check app/` — Python linting
   - `uv run ruff format --check app/` — Python formatting
   - `uv run pytest tests/unit/ -v` — Unit tests

2. **Frontend Checks (services/frontend/)**

   Run these commands:
   - `bun run lint` — ESLint for Vue/TypeScript
   - `bunx vue-tsc --noEmit` — TypeScript type checking
   - `bun run test` — Vitest unit tests

3. **Aggregate Results**

   If any check fails:
   - Display which checks failed
   - Show error summary
   - Suggest running specific command for details
   - Exit with failure

   If all pass:
   - Show summary: "All checks passed"
   - Include test counts if available

**Output On Success**

```
## Project Checks ✓

**Backend:**
- ruff:     OK
- pytest:   OK (N tests passed)

**Frontend:**
- ESLint:   OK
- vue-tsc:  OK
- vitest:   OK (N tests passed)

All checks passed!
```

**Output On Failure**

```
## Project Checks ✗

**Backend:**
- ruff:     ✗ FAILED
- pytest:   OK/PASSED

**Frontend:**
- ESLint:   OK/PASSED
- vue-tsc:  ✗ FAILED
- vitest:   OK/PASSED

Failed checks: ruff, vue-tsc

Run the following for details:
  cd services/backend && uv run ruff check app/
  cd services/frontend && bunx vue-tsc --noEmit
```

**Guardrails**

- Run all checks even if one fails (to show full picture)
- Do NOT make changes — only check and report
- Use correct working directories as specified
- Always use absolute paths when calling tools
