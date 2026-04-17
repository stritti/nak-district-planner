---
name: checks
description: Run code quality checks. Executes Ruff, Bandit, pytest for backend and ESLint, TypeScript, Vitest for frontend.
license: MIT
metadata:
  author: Claude
  version: "1.0"
---

Run code quality checks to verify code changes.

**Input**: None required. Checks both backend and frontend.

**Steps**

1. **Backend Checks (services/backend/)**

   Run these commands:
   ```bash
   cd services/backend && uv run ruff check app/ tests/
   cd services/backend && uv run ruff format --check app/ tests/
   cd services/backend && uv run pytest tests/unit/ -v
   cd services/backend && uv run bandit -r app/ -ll
   ```

2. **Frontend Checks (services/frontend/)**

   Run these commands:
   ```bash
   cd services/frontend && bun run lint
   cd services/frontend && bun run build
   cd services/frontend && bun run test
   ```

3. **Docker Compose Validation**

   ```bash
   docker compose config --quiet
   ```

4. **Aggregate Results**

   If any check fails:
   - Display which checks failed
   - Show error summary
   - Exit with failure

   If all pass:
   - Show summary: "All checks passed"

**Output On Success**

```text
## Checks ✓

Backend:
- ruff check:  OK
- ruff format: OK
- pytest:     OK
- bandit:    OK

Frontend:
- ESLint:     OK
- build:      OK
- Vitest:     OK

All checks passed!
```

**Output On Failure**

```text
## Checks ✗

Backend:
- ruff check:  ✗ FAILED
- pytest:     OK

Frontend:
- ESLint:     ✗ FAILED

Failed: ruff check, ESLint
```

**Guardrails**

- Run all checks even if one fails
- Do NOT make changes — only check and report
- Use correct working directories