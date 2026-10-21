# Export Token Contract RLS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Deliver the accepted OpenSpec change with regression tests and safe rollout.

**Architecture:** Follow the approved component boundaries in the linked OpenSpec design. Use test-first changes in isolated GitHub branches; each production behavior requires a verified red-to-green cycle and independent code review.

**Tech Stack:** Python 3.14; FastAPI; SQLAlchemy; PostgreSQL 18; pytest; uv; GitHub Actions; OpenSpec.

**Spec:** `openspec/changes/export-token-contract-rls-tests/design.md` and `openspec/changes/export-token-contract-rls-tests/specs/export-tokens/spec.md`

## Global Constraints

- Clean Code; test exceptions and concurrency; backend coverage >=80%.
- Preserve RLS tenant isolation and redact credentials.
- Avoid modifications to unrelated application functionality.
- This PR remains Draft until implementation and CI verification.
- Test execution must use the repository's real PostgreSQL CI services where needed.

## Review Focus

- Revoked token still matches a cached function result: denied
- PUBLIC vs INTERNAL scope mismatch on unpublished event: denied
- Cross-district personal subject overlapping names: denied
- App role accidentally owns protected schema: test fails
- Policy contains old plaintext field in nested function: reject

---

### Task 1: Disposable upgrade with restricted app role

**Files:** `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`.

- [ ] **Step 1 — RED:** Add `test_upgraded_runtime_role_is_not_owner_or_bypassrls: inspect pg_roles and pg_class on migrated disposable database` in `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration/test_export_token_contract_upgrade_postgres.py -k runtime_role -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`, reuse existing fresh-db fixture; connect APP_DB_USER using RLS_TEST_APP_PASSWORD; no owner queries in acceptance assertions.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration/test_export_token_contract_upgrade_postgres.py -k runtime_role -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 2: Subscription behavior matrix

**Files:** `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`.

- [ ] **Step 1 — RED:** Add `test_contract_preserves_public_internal_personal_and_revoked_scopes: two districts, subject and token transaction GUCs, unknown and revoked tokens` in `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration/test_export_token_contract_upgrade_postgres.py -k contract_preserves -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`, compare observable row sets to pre-upgrade policy semantics; include foreign tenant, no current subject and application role.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration/test_export_token_contract_upgrade_postgres.py -k contract_preserves -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 3: SQL definition equivalence

**Files:** `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py; services/backend/app/adapters/db/migrations/rls_policies.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`.

- [ ] **Step 1 — RED:** Add `test_contract_contains_no_plaintext_dependencies: inspect pg_policies and pg_proc post migration; use normalized known-good references` in `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration/test_export_token_contract_upgrade_postgres.py -k plaintext_dependencies -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`, assert removed token column and no export_tokens.token expressions; do not auto-regenerate expected snapshot.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration/test_export_token_contract_upgrade_postgres.py -k plaintext_dependencies -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 4: CI role preflight

**Files:** `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py; .github/workflows/ci.yml`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`.

- [ ] **Step 1 — RED:** Add `test_missing_application_role_is_not_false_positive: fail explicitly if integration CI has absent app-role credentials` in `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration tests/unit --cov=app --cov-fail-under=80 -q`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/integration/test_export_token_contract_upgrade_postgres.py`, keep disposable DB teardown in finally; confirm CI postgres + app credentials and coverage.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration tests/unit --cov=app --cov-fail-under=80 -q`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

## Final Verification and Review

- [ ] Run Ruff (`cd services/backend && uv run ruff check .`) and OpenSpec validation.
- [ ] Run CI integration, unit, PostgreSQL RLS, performance and migration workflows for latest SHA.
- [ ] Report exact test totals and measured backend coverage >=80%; no inference from older commits.
- [ ] Request a fresh Codex review, fix blocking findings, and record unresolved operational gates.
- [ ] Mark PR ready only after all checks pass; do not auto-merge.

## Decisions requiring operator evidence

The acceptance test must connect as a genuinely restricted non-owner DB role and must check runtime-scoped rows, not owner-scoped results.
