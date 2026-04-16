---
name: project-checks
description: Run fast project quality checks after code changes. Executes Ruff, ESLint, type checking, and tests for both backend and frontend.
license: MIT
metadata:
  author: Claude
  version: "2.0"
---

Run fast project quality checks to verify code changes. Use `quality-checks` skill for comprehensive checks including MegaLinter, Bandit, and Docker.

**Input**: None required. Checks both backend and frontend.

**Steps**

1. **Backend Checks (services/backend/)**

   Run these commands:
   - `uv run ruff check app/ tests/` — Python linting
   - `uv run ruff format --check app/ tests/` — Python formatting
   - `uv run pytest tests/unit/ -v` — Unit tests

2. **Frontend Checks (services/frontend/)**

   Run these commands:
   - `bun run lint` — ESLint for Vue/TypeScript
   - `bun run build` — TypeScript + Vue build check
   - `bun run test` — Vitest unit tests

3. **Docker Compose Validation**

   ```bash
   docker compose config --quiet
   ```

4. **Aggregate Results**

   If any check fails:
   - Display which checks failed
   - Show error summary
   - Suggest running specific command for details
   - Exit with failure

   If all pass:
   - Show summary: "All checks passed"
   - Include test counts if available

**Output On Success**

```text
## Project Checks ✓

**Backend:**
- ruff check:       OK
- ruff format:      OK
- pytest:          OK (N tests passed)

**Frontend:**
- ESLint:           OK
- build:            OK
- Vitest:           OK (N tests passed)

**Infrastructure:**
- Docker Compose:   OK

All checks passed!
```

**Output On Failure**

```text
## Project Checks ✗

**Backend:**
- ruff check:       ✗ FAILED
- pytest:           OK (N tests passed)

**Frontend:**
- ESLint:           ✗ FAILED
- build:            OK

**Infrastructure:**
- Docker Compose:    OK

Failed checks: ruff check, ESLint

Run the following for details:
  cd services/backend && uv run ruff check app/ tests/
  cd services/frontend && bun run lint
```

**Guardrails**

- Run all checks even if one fails (to show full picture)
- Do NOT make changes — only check and report
- Use correct working directories as specified
- Always use absolute paths when calling tools
