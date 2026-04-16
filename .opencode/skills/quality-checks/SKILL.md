---
name: quality-checks
description: Run comprehensive quality checks on code changes. Executes MegaLinter, Ruff, Bandit, ESLint, TypeScript, and tests for both backend and frontend.
license: MIT
metadata:
  author: Claude
  version: "2.0"
---

Run comprehensive quality checks to verify code changes.

**Input**: None required. Checks both backend and frontend.

**Steps**

1. **Detect Changed Files**

   Identify which files changed to determine which checks to run:
   - Backend: `services/backend/**/*.{py,toml,yml}`
   - Frontend: `services/frontend/**/*.{ts,vue,json}`
   - Config: `.mega-linter.yml`, `Dockerfile*`, `docker-compose*.yml`
   - Docs: `**/*.md`

2. **Backend Checks (services/backend/)**

   Run these commands (always run if backend files changed):
   ```bash
   cd services/backend && uv run ruff check app/ tests/
   cd services/backend && uv run ruff format --check app/ tests/
   cd services/backend && uv run pytest tests/unit/ -v
   cd services/backend && uv run bandit -r app/ -ll
   ```

3. **Frontend Checks (services/frontend/)**

   Run these commands (always run if frontend files changed):
   ```bash
   cd services/frontend && bun run lint
   cd services/frontend && bun run build
   cd services/frontend && bun run test
   ```

4. **MegaLinter (optional - full repo)**

   Run MegaLinter for cross-language checks:
   ```bash
   docker run --rm -v $(pwd):/tmp/lint ghcr.io/oxsecurity/megalinter:latest
   ```

   Or use megalinter-runner if installed:
   ```bash
   megalinter
   ```

5. **Docker Checks (if Dockerfiles changed)**

   ```bash
   cd services/backend && hadolint Dockerfile
   cd services/frontend && hadolint Dockerfile
   docker compose config --quiet
   ```

6. **Aggregate Results**

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
## Quality Checks ✓

**Backend:**
- ruff check:       OK
- ruff format:      OK
- pytest:           OK (N tests passed)
- bandit:           OK (0 issues)

**Frontend:**
- ESLint:           OK
- TypeScript:       OK
- Vitest:           OK (N tests passed)

**Infrastructure:**
- Docker Compose:    OK

All checks passed!
```

**Output On Failure**

```text
## Quality Checks ✗

**Backend:**
- ruff check:       ✗ FAILED
- pytest:           OK (N tests passed)

**Frontend:**
- ESLint:           ✗ FAILED
- TypeScript:       OK

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
- Skip tests if no test files changed (optional, configurable)
- Docker checks only if Docker files changed

**Tool Requirements**

- Backend: `uv` for Python package management
- Frontend: `bun` for JavaScript package management
- Optional: `docker` for MegaLinter, `hadolint` for Dockerfile linting
