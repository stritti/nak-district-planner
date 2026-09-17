# Open Review Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die offenen Findings aus PR #208 in unabhängig reviewbare, getestete Pull Requests überführen.

**Architecture:** Sicherheits- und Betriebsänderungen bleiben im Backend und werden mit fokussierten Unit-/Integrationstests abgesichert. Das Sync-Refactoring erhält eine typisierte Ergebnisgrenze zwischen Application-Service und Celery/API-Adaptern. Frontend-PRs extrahieren ausschließlich Darstellung und lokale Interaktion aus bestehenden Views, ohne Store- oder API-Verhalten zu ändern.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2, pytest/pytest-cov, OpenTelemetry, Celery; Vue 3 Composition API, TypeScript, Pinia, Vitest, bun.

## Global Constraints

- Keine Secrets, Test-Credentials oder Produktionsdaten committen.
- Pydantic v2 für API-Eingaben verwenden.
- Domain-Code darf nicht von FastAPI oder SQLAlchemy abhängen.
- Keine fachliche Verhaltensänderung in PR-8, PR-9 oder PR-11.
- Sicherheitsänderungen benötigen positive und negative Tests.
- Jeder PR erhält einen eigenen Branch, Commit, Push, PR-Titel, Beschreibung und Checklauf.
- Nicht zugehörige lokale Änderungen dürfen nicht überschrieben oder mitgestaged werden.

---

## Task 1: B-4 — JWT-Claims-Coverage erhöhen

**Files:**
- Modify: `services/backend/app/adapters/auth/jwt_claims.py` only if coverage exposes an untested branch that needs a safe correction
- Test: `services/backend/tests/unit/test_auth_permissions_jwt_claims.py`
- Inspect: `services/backend/pyproject.toml`, `.github/workflows/ci.yml`

**Interfaces:**
- Consumes existing JWT claim parsing/validation APIs.
- Produces a measured `app/adapters/auth` coverage report with JWT-Claims at or above 90%.

- [ ] Write tests for every currently uncovered JWT-Claims branch, including missing claims, malformed claim values, valid membership claims, expired/invalid metadata, and empty membership collections.
- [ ] Run the focused test file and coverage command:
  `cd services/backend && uv run pytest tests/unit/test_auth_permissions_jwt_claims.py --cov=app/adapters/auth/jwt_claims.py --cov-report=term-missing -q`.
- [ ] Add only minimal implementation changes required by a discovered defect; do not weaken validation to improve coverage.
- [ ] Run the complete auth unit subset:
  `cd services/backend && uv run pytest tests/unit/ -k 'auth or permission or jwt' -q`.
- [ ] Record the measured percentage and remaining exclusions in the PR description.
- [ ] Commit as `test: raise JWT claims coverage to target` and open a dedicated B-4 PR.

## Task 2: B-3 — Product decision for external sync review workflow

**Files:**
- Modify: `docs/use-cases.md` (UC-02)
- Modify: `docs/code-review-2026-07.md`
- Modify: `docs/code-review-2026-07-action-plan.md`
- Do not create: `ExternalEventCandidate` implementation without explicit product approval

**Interfaces:**
- Consumes existing `SyncState`/`ExternalEventLink` behavior.
- Produces an explicit v1 decision and a documented Phase-2 limitation if review workflow is deferred.

- [ ] Document that imported external events are accepted directly for v1 unless a product owner requires manual review.
- [ ] State the operational consequence and trusted-source assumption in UC-02.
- [ ] Update the review action plan so B-3 is either “accepted for v1 / Phase 2” or “implementation required”; never mark it completed without the decision.
- [ ] Review links and terminology against the current `SyncState` and `ExternalEventLink` code.
- [ ] Commit as `docs: record external sync review decision` and open a decision PR.

## Task 3: PR-5 — Rate-limiter fail-open observability

**Files:**
- Modify: `services/backend/app/application/rate_limiter.py`
- Modify: `services/backend/app/adapters/api/middleware/rate_limit.py` only if propagation is required
- Test: existing rate-limiter tests under `services/backend/tests/unit/`
- Modify: `docs/production-runbook.md` and/or `docs/security/rate-limiting.md`

**Interfaces:**
- Consumes the existing OpenTelemetry setup and `record_fail_open_metric` pathway.
- Produces a stable metric name/attribute contract and an operator response note.

- [ ] Locate the existing fail-open counter implementation and add/complete a test that increments it when Redis access fails.
- [ ] Add a negative test proving normal allowed requests do not falsely increment the fail-open counter.
- [ ] Keep metric labels bounded; do not include user IDs, tokens, or raw request data.
- [ ] Document metric name, meaning, alert threshold guidance, and recovery action in the runbook.
- [ ] Run focused rate-limiter tests and lint.
- [ ] Commit as `feat: expose rate limiter fail-open observability` and open the PR.

## Task 4: PR-7 — Health-check and audit-log verification

**Files:**
- Inspect/Modify: `services/backend/app/main.py` health endpoint
- Inspect/Modify: `services/backend/app/adapters/api/middleware/audit.py`
- Inspect/Modify: `services/backend/app/application/audit_service.py`
- Inspect: `docker-compose.yml`
- Test: existing health/audit tests under `services/backend/tests/`
- Modify: `docs/production-runbook.md`

**Interfaces:**
- Consumes existing database, Valkey/Redis, middleware, and audit queue abstractions.
- Produces deterministic health semantics and tests for representative security-sensitive mutations.

- [ ] Add a failing test for the expected health response when the database and cache dependencies are healthy.
- [ ] Add a failing test for dependency failure, asserting a non-healthy response without leaking credentials or stack traces.
- [ ] Add audit assertions for a role change, registration decision, and export-token creation using the existing audit abstraction.
- [ ] Verify Docker Compose healthcheck points to the canonical health endpoint; change only if the current configuration is wrong.
- [ ] Run focused health/audit tests and `docker compose config --quiet`.
- [ ] Document the verified checks and operator interpretation in the production runbook.
- [ ] Commit as `test: verify health and audit logging readiness` and open the PR.

## Task 5: PR-8 — Sync connector registry and typed result

**Files:**
- Create/Modify: `services/backend/app/application/sync/results.py`
- Modify: `services/backend/app/application/sync_service.py`
- Modify: `services/backend/app/application/tasks.py`
- Modify: API response adapter only where the existing dict result is serialized
- Test: `services/backend/tests/unit/test_sync_service.py` and related task tests
- Reference: `openspec/changes/code-quality/design.md`, `openspec/changes/code-quality/tasks.md`

**Interfaces:**
- Produces `SyncResult(created: int, updated: int, cancelled: int, errors: int)` as the service result.
- Produces `_CONNECTOR_MAP: dict[CalendarType, type[CalendarConnector]]` with the same supported calendar types and explicit unsupported behavior.

- [ ] Add failing tests for every supported `CalendarType`, unsupported type behavior, and `SyncResult` field values.
- [ ] Add the dataclass with explicit integer fields and a stable serialization helper only if callers need JSON output.
- [ ] Replace the connector `if/elif` chain with `_CONNECTOR_MAP` while preserving constructor dependencies and error behavior.
- [ ] Update Celery/API callers without changing event deduplication, cancellation, or credential handling.
- [ ] Run the complete sync-focused test subset and type/lint checks.
- [ ] Commit as `refactor: type sync results and connector registry` and open the PR.

## Task 6: PR-6 — Documentation cleanup after technical PRs

**Files:**
- Modify: `docs/openspec-gap-analysis.md`
- Modify: `docs/rbac-completion-plan.md`
- Modify: `docs/architecture-status.md`
- Modify: `docs/improvement-proposals.md`
- Create: `docs/rbac-coverage.md` only if endpoint evidence is current and complete
- Modify: `docs/code-review-2026-07.md`
- Modify: `docs/code-review-2026-07-action-plan.md`

**Interfaces:**
- Consumes merged evidence from PRs B-4, PR-5, PR-7, and PR-8.
- Produces no executable behavior changes; all claims link to current code or tests.

- [ ] Re-audit every status claim against merged commit hashes before editing.
- [ ] Mark historical analysis as historical, not deleted, and preserve links for context.
- [ ] Update architecture/security status only where the implementation and verification are complete.
- [ ] Remove duplicate contradictory PR-6 sections or label one as historical backlog so the document has one authoritative status.
- [ ] Run markdown lint/checks on changed documentation.
- [ ] Commit as `docs: reconcile review status with merged work` and open the PR.

## Task 7: PR-9a — Matrix view decomposition

**Files:**
- Modify: `services/frontend/src/views/MatrixView.vue`
- Create: `services/frontend/src/components/matrix/MatrixFilters.vue`
- Create: `services/frontend/src/components/matrix/MatrixTable.vue`
- Test: existing Matrix Vitest tests; add focused component tests if missing

**Interfaces:**
- Props/emits must preserve current filter and assignment behavior.
- Store/API contracts remain unchanged.

- [ ] Capture existing behavior with focused tests before extraction.
- [ ] Extract filters first, preserving `v-model`/emit names and accessibility labels.
- [ ] Extract table rendering second, preserving slot/event payloads and loading/empty/error states.
- [ ] Run `cd services/frontend && bun run lint && bun run build && bun run test`.
- [ ] Commit and open a standalone Matrix PR.

## Task 8: PR-9b–PR-9e — Remaining frontend views

**Files:**
- PR-9b: `LeadersAdminView.vue` plus focused form/list components
- PR-9c: `EventListView.vue` plus `EventFilters.vue`, `EventTable.vue`, `EventFormModal.vue`
- PR-9d: `CalendarIntegrationsView.vue` plus `IntegrationCard.vue`, `IntegrationFormModal.vue`
- PR-9e: `DistrictsAdminView.vue` only where a stable extraction boundary is demonstrated

**Interfaces:**
- Each PR preserves route, Pinia store, API client, permissions, confirmation dialogs, toasts, and emitted event payloads.

- [ ] Add or update focused tests before each extraction.
- [ ] Extract one responsibility at a time and keep copy/visual behavior unchanged.
- [ ] Run frontend lint, type/build, and relevant Vitest tests after each PR.
- [ ] Open each view extraction as a separate PR; do not combine unrelated views.

## Task 9: PR-11 — Optional encrypted JSON TypeDecorator

**Files:**
- Create: `services/backend/app/adapters/db/types.py` or the project’s established DB type module
- Modify: calendar integration ORM model
- Modify: `services/backend/app/application/crypto.py` only if a typed adapter boundary is needed
- Test: crypto and calendar integration unit/integration tests

**Interfaces:**
- The type transparently encrypts on bind and decrypts on result while preserving the existing Python mapping type.
- Existing plaintext/migration handling must be explicit; no silent data loss or accidental double encryption.

- [ ] First add round-trip, null, malformed ciphertext, and migration-compatibility tests.
- [ ] Implement the smallest SQLAlchemy `TypeDecorator` compatible with the current encryption service.
- [ ] Verify generated SQL never logs or exposes plaintext credentials.
- [ ] Run crypto, DB adapter, and integration tests; abandon the PR if compatibility cannot be proven.
- [ ] Commit as `refactor: encapsulate encrypted credentials in db type` and open the optional PR.

## Verification and PR handoff

- [ ] Run backend focused tests plus Ruff/format checks for backend PRs.
- [ ] Run frontend lint, type/build, and Vitest for frontend PRs.
- [ ] Run `docker compose config --quiet` for infrastructure-affecting PRs.
- [ ] Inspect `git diff`, `git status`, and commit history before each push.
- [ ] Open PRs with scope, tests, risk, and dependency links; never claim a PR is complete without fresh command output.
