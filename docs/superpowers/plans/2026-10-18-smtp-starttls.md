# SMTP STARTTLS Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Deliver the accepted OpenSpec change with regression tests and safe rollout.

**Architecture:** Follow the approved component boundaries in the linked OpenSpec design. Use test-first changes in isolated GitHub branches; each production behavior requires a verified red-to-green cycle and independent code review.

**Tech Stack:** Python 3.14; FastAPI; SQLAlchemy; PostgreSQL 18; pytest; uv; GitHub Actions; OpenSpec.

**Spec:** `openspec/changes/starttls-smoke-verification/design.md` and `openspec/changes/starttls-smoke-verification/specs/mail-notifications/spec.md`

## Global Constraints

- Clean Code; test exceptions and concurrency; backend coverage >=80%.
- Preserve RLS tenant isolation and redact credentials.
- Avoid modifications to unrelated application functionality.
- This PR remains Draft until implementation and CI verification.
- Test execution must use the repository's real PostgreSQL CI services where needed.

## Review Focus

- Client/server certificate CN without SAN: reject hostname mismatch
- TLS upgrade works but second EHLO fails: no AUTH
- AUTH capability not advertised after TLS: client fails safely
- Duplicate recipients cause extra messages: one per unique address
- Protocol failure log exposes configured credentials: scrub

---

### Task 1: Local ephemeral SMTP harness

**Files:** `services/backend/tests/integration/test_smtp_starttls.py; services/backend/pyproject.toml; services/backend/uv.lock`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_smtp_starttls.py`.

- [ ] **Step 1 — RED:** Add `test_trusted_starttls_server_authenticates_only_after_handshake: observed SMTP AUTH only after server TLS upgraded` in `services/backend/tests/integration/test_smtp_starttls.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration/test_smtp_starttls.py::test_trusted_starttls_server_authenticates_only_after_handshake -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/integration/test_smtp_starttls.py`, run loopback server on port 0; ephemeral certificate SAN; test CA trust, never turn off hostname verification.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration/test_smtp_starttls.py::test_trusted_starttls_server_authenticates_only_after_handshake -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 2: Fail-closed TLS cases

**Files:** `services/backend/tests/integration/test_smtp_starttls.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_smtp_starttls.py`.

- [ ] **Step 1 — RED:** Add `test_auth_not_sent_without_starttls, test_untrusted_cert_blocks_auth, test_hostname_mismatch_blocks_auth, test_broken_handshake_blocks_auth` in `services/backend/tests/integration/test_smtp_starttls.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration/test_smtp_starttls.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/integration/test_smtp_starttls.py`, record protocol ordering and accepted DATA; no credentials in trace/logs; verify exception contract MailDeliveryError.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration/test_smtp_starttls.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 3: Relay handshake preflight

**Files:** `services/backend/scripts/check_smtp_starttls.py; docs/operations/production-runbook.md`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/unit/test_smtp_starttls_check.py`.

- [ ] **Step 1 — RED:** Add `test_relay_preflight_does_not_send_auth_or_mail: verify certificate validation and EHLO/STARTTLS/EHLO then QUIT` in `services/backend/tests/unit/test_smtp_starttls_check.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/unit/test_smtp_starttls_check.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/scripts/check_smtp_starttls.py`, safe non-delivering operator command, secrets never printed, explicit hostname & cert diagnostics.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/unit/test_smtp_starttls_check.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 4: CI and regressions

**Files:** `services/backend/tests/integration/test_smtp_starttls.py; .github/workflows/ci.yml`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_smtp_starttls.py`.

- [ ] **Step 1 — RED:** Add `test_smtp_noauth_relay_path: auth disabled, test server accepts mail only in intended mode` in `services/backend/tests/integration/test_smtp_starttls.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/unit tests/integration --cov=app --cov-fail-under=80 -q`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/integration/test_smtp_starttls.py`, cI without external SMTP, document separate live stage smoke gate.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/unit tests/integration --cov=app --cov-fail-under=80 -q`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

## Final Verification and Review

- [ ] Run Ruff (`cd services/backend && uv run ruff check .`) and OpenSpec validation.
- [ ] Run CI integration, unit, PostgreSQL RLS, performance and migration workflows for latest SHA.
- [ ] Report exact test totals and measured backend coverage >=80%; no inference from older commits.
- [ ] Request a fresh Codex review, fix blocking findings, and record unresolved operational gates.
- [ ] Mark PR ready only after all checks pass; do not auto-merge.

## Decisions requiring operator evidence

Local tests do not certify the deployed SMTP relay: a real staging handshake and verification record are required.
