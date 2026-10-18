# Durable Audit Outbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Deliver the accepted OpenSpec change with regression tests and safe rollout.

**Architecture:** Follow the approved component boundaries in the linked OpenSpec design. Use test-first changes in isolated GitHub branches; each production behavior requires a verified red-to-green cycle and independent code review.

**Tech Stack:** Python 3.14; FastAPI; SQLAlchemy; PostgreSQL 18; pytest; uv; GitHub Actions; OpenSpec.

**Spec:** `openspec/changes/durable-audit-outbox/design.md` and `openspec/changes/durable-audit-outbox/specs/audit-logging/spec.md`

## Global Constraints

- Clean Code; test exceptions and concurrency; backend coverage >=80%.
- Preserve RLS tenant isolation and redact credentials.
- Avoid modifications to unrelated application functionality.
- This PR remains Draft until implementation and CI verification.
- Test execution must use the repository's real PostgreSQL CI services where needed.

## Review Focus

- Concurrent dispatcher crash between audit insert and outbox acknowledgement: idempotent row
- RLS context lost on database reconnect: no cross-tenant visibility
- Poisoned payload from older release: quarantine without head-of-line blocking
- Transaction retry after a network-ambiguous commit: stable event ID
- Read-only HTTP denial while DB unavailable: failure reported rather than silent audit omission

---

### Task 1: Transactional acceptance / missing tenant

**Files:** `services/backend/app/adapters/db/domain_audit.py; services/backend/app/adapters/db/session.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_audit_outbox_postgres.py`.

- [ ] **Step 1 — RED:** Add `test_unresolved_audited_tenant_aborts_business_transaction: insert a protected object with an unresolved tenant, assert no write or audit outcome is committed` in `services/backend/tests/integration/test_audit_outbox_postgres.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration/test_audit_outbox_postgres.py::test_unresolved_audited_tenant_aborts_business_transaction -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/app/adapters/db/domain_audit.py`, raise a typed AuditPersistenceError rather than ignoring an entry; explicitly include non-ORM bulk paths.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration/test_audit_outbox_postgres.py::test_unresolved_audited_tenant_aborts_business_transaction -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 2: Persistent PostgreSQL outbox schema

**Files:** `services/backend/alembic/versions/<new_revision>_audit_outbox.py; services/backend/app/adapters/db/orm_models/audit_outbox.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_audit_outbox_postgres.py`.

- [ ] **Step 1 — RED:** Add `test_audit_outbox_is_transactional_and_role_scoped: verify rollback, role grants, RLS and unchanged existing audit records` in `services/backend/tests/integration/test_audit_outbox_postgres.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration/test_audit_outbox_postgres.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/alembic/versions/<new_revision>_audit_outbox.py`, create event_id UUID PK; immutable payload; tenant keys; retry state; indexes; grants/RLS; insert from after_flush on same connection.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration/test_audit_outbox_postgres.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 3: Idempotent dispatch

**Files:** `services/backend/app/adapters/worker/audit_outbox_tasks.py; services/backend/app/application/audit_outbox_dispatcher.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/integration/test_audit_outbox_delivery.py`.

- [ ] **Step 1 — RED:** Add `test_two_workers_deliver_only_one_audit_event: claim using SKIP LOCKED; simulate retry after committed delivery and verify one final row` in `services/backend/tests/integration/test_audit_outbox_delivery.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/integration/test_audit_outbox_delivery.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/app/adapters/worker/audit_outbox_tasks.py`, batch <= 100; stable event_id = audit_logs.id; delivery+ack atomic; exponential backoff capped 300 seconds; quarantine poison rows.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/integration/test_audit_outbox_delivery.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 4: HTTP audit guarantees

**Files:** `services/backend/app/adapters/api/middleware/audit.py; services/backend/app/application/audit_service.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/unit/test_audit_middleware.py; services/backend/tests/integration/test_audit_outbox_postgres.py`.

- [ ] **Step 1 — RED:** Add `test_denied_request_persists_before_response and test_failed_domain_audit_refuses_success; verify DB session setup/commit faults` in `services/backend/tests/unit/test_audit_middleware.py; services/backend/tests/integration/test_audit_outbox_postgres.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/unit/test_audit_middleware.py tests/integration/test_audit_outbox_postgres.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/app/adapters/api/middleware/audit.py`, remove silent exception swallowing and lossy acknowledgement; separate HTTP-denial transaction from business write, do not claim post-commit rollback.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/unit/test_audit_middleware.py tests/integration/test_audit_outbox_postgres.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 5: Operational evidence

**Files:** `services/backend/app/telemetry.py; docs/operations/production-runbook.md; .github/workflows/ci.yml`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/unit/test_audit_outbox_dispatcher.py`.

- [ ] **Step 1 — RED:** Add `test_shutdown_preserves_unfinished_events and test_backoff_has_cap_and_no_unbounded_queue` in `services/backend/tests/unit/test_audit_outbox_dispatcher.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/unit tests/integration -q`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/app/telemetry.py`, define <=10s stop, backlog/oldest-age/retry/quarantine metrics, alarms, outage drill, rollback/upgrade notes.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/unit tests/integration -q`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

## Final Verification and Review

- [ ] Run Ruff (`cd services/backend && uv run ruff check .`) and OpenSpec validation.
- [ ] Run CI integration, unit, PostgreSQL RLS, performance and migration workflows for latest SHA.
- [ ] Report exact test totals and measured backend coverage >=80%; no inference from older commits.
- [ ] Request a fresh Codex review, fix blocking findings, and record unresolved operational gates.
- [ ] Mark PR ready only after all checks pass; do not auto-merge.

## Decisions requiring operator evidence

Fail-closed requires the mutation and audit intent to share the database transaction. A post-response middleware cannot retroactively roll back a successful commit.
