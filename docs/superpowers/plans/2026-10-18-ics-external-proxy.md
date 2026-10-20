# External ICS Proxy Log Redaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Deliver the accepted OpenSpec change with regression tests and safe rollout.

**Architecture:** Follow the approved component boundaries in the linked OpenSpec design. Use test-first changes in isolated GitHub branches; each production behavior requires a verified red-to-green cycle and independent code review.

**Tech Stack:** Python 3.14; FastAPI; SQLAlchemy; PostgreSQL 18; pytest; uv; GitHub Actions; OpenSpec.

**Spec:** `openspec/changes/external-ics-proxy-redaction/design.md` and `openspec/changes/external-ics-proxy-redaction/specs/export-tokens/spec.md`

## Global Constraints

- Clean Code; test exceptions and concurrency; backend coverage >=80%.
- Preserve RLS tenant isolation and redact credentials.
- Avoid modifications to unrelated application functionality.
- This PR remains Draft until implementation and CI verification.
- Test execution must use the repository's real PostgreSQL CI services where needed.

## Review Focus

- Proxy logs RequestURI despite path filter: no canary pass
- Central traces leak URL after proxy suppression: fail
- Prior logs retained with valid credentials: revoke/reissue
- Unavailable sink interpreted as clean: fail
- Verification tool prints token on test failure: redact

---

### Task 1: Threat model and proxy-safe defaults

**Files:** `docs/operations/production-runbook.md`; `services/backend/tests/unit/test_proxy_log_redaction_documentation.py`

**Interfaces:** Produces a documented nginx-safe logging configuration validated by `services/backend/tests/unit/test_proxy_log_redaction_documentation.py`.

- [ ] **Step 1 — RED:** Add `test_proxy_log_configuration_uses_original_request_and_suppresses_errors` in `services/backend/tests/unit/test_proxy_log_redaction_documentation.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `python -m pytest services/backend/tests/unit/test_proxy_log_redaction_documentation.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `docs/operations/production-runbook.md`, avoid claiming Traefik accessLog.filters edits arbitrary URI; prefer path logging off when cannot prove sanitation.
- [ ] **Step 4 — Verify green:** `python -m pytest services/backend/tests/unit/test_proxy_log_redaction_documentation.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 2: Canary/telemetry audit procedure

**Files:** `docs/operations/production-runbook.md; scripts/check_ics_canary_logs.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/unit/test_external_ics_canary.py`.

- [ ] **Step 1 — RED:** Add `test_verifier_returns_only_status_not_token: feed URL and telemetry sink allowlist; fail closed if sink unavailable` in `services/backend/tests/unit/test_external_ics_canary.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/unit/test_external_ics_canary.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** Implement `scripts/check_ics_canary_logs.py` (token via stdin, status-only output) and document it in `docs/operations/production-runbook.md`; the canary must never echo/persist the token; check proxy, APM, spans and central logs.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/unit/test_external_ics_canary.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 3: Rotation and evidence template

**Files:** `docs/operations/production-runbook.md`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/unit/test_external_ics_canary.py`.

- [ ] **Step 1 — RED:** Add `test_incomplete_checks_cannot_pass: lack of operator proof leaves issue open` in `services/backend/tests/unit/test_external_ics_canary.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/unit/test_external_ics_canary.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `docs/operations/production-runbook.md`, operator/version/date/sinks/retention/revoked token count; no secret-bearing evidence.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/unit/test_external_ics_canary.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

## Final Verification and Review

- [ ] Run Ruff (`cd services/backend && uv run ruff check .`) and OpenSpec validation.
- [ ] Run CI integration, unit, PostgreSQL RLS, performance and migration workflows for latest SHA.
- [ ] Report exact test totals and measured backend coverage >=80%; no inference from older commits.
- [ ] Request a fresh Codex review, fix blocking findings, and record unresolved operational gates.
- [ ] Mark PR ready only after all checks pass; do not auto-merge.

## Decisions requiring operator evidence

The live external TLS proxy and all observability sinks are out of repository scope: keep issue #629 open until operator's canary and historical-log checks are proven.
