# Event List Query Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`).

**Goal:** Deliver the accepted OpenSpec change with regression tests and safe rollout.

**Architecture:** Follow the approved component boundaries in the linked OpenSpec design. Use test-first changes in isolated GitHub branches; each production behavior requires a verified red-to-green cycle and independent code review.

**Tech Stack:** Python 3.14; FastAPI; SQLAlchemy; PostgreSQL 18; pytest; uv; GitHub Actions; OpenSpec.

**Spec:** `openspec/changes/event-list-query-performance/design.md` and `openspec/changes/event-list-query-performance/specs/event-listing/spec.md`

## Global Constraints

- Clean Code; test exceptions and concurrency; backend coverage >=80%.
- Preserve RLS tenant isolation and redact credentials.
- Avoid modifications to unrelated application functionality.
- This PR remains Draft until implementation and CI verification.
- Test execution must use the repository's real PostgreSQL CI services where needed.

## Review Focus

- Huge OFFSET with small LIMIT: bounded query resources
- Slow COUNT independent of page selection: measured separately
- Planner with empty group: no unintended all-tenant data
- ANY array skew causing sequential scan: measured
- Timeout interrupted transaction not returned as HTTP 200: test

---

### Task 1: Large disposable fixture

**Files:** `services/backend/tests/performance/test_event_listing_query_plans.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/performance/test_event_listing_query_plans.py`.

- [ ] **Step 1 — RED:** Add `test_bulk_fixture_is_tenant_isolated: 25 congregations and 50k slots, deterministic seed, second tenant, fixture cleanup on error` in `services/backend/tests/performance/test_event_listing_query_plans.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/performance/test_event_listing_query_plans.py -k fixture -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/performance/test_event_listing_query_plans.py`, bulk insertion in disposable PostgreSQL schema; use realistic cardinality and no production data.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/performance/test_event_listing_query_plans.py -k fixture -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 2: Observe real count and page statements

**Files:** `services/backend/app/adapters/db/repositories/planning_slot.py; services/backend/tests/performance/test_event_listing_query_plans.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/performance/test_event_listing_query_plans.py`.

- [ ] **Step 1 — RED:** Add `test_filtered_count_and_page_plans: EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) against bound SQL for district, congregation, ANY(applicability), offsets 0 and 10000` in `services/backend/tests/performance/test_event_listing_query_plans.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/performance/test_event_listing_query_plans.py -k plans -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/app/adapters/db/repositories/planning_slot.py`, record real plan and buffer data for existing total and page queries, assert returned rows and tenancy.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/performance/test_event_listing_query_plans.py -k plans -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 3: Timeout and API decision record

**Files:** `docs/operations/event-list-performance.md; services/backend/tests/performance/test_event_listing_query_plans.py`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/performance/test_event_listing_query_plans.py`.

- [ ] **Step 1 — RED:** Add `test_statement_timeout_is_reported: SET LOCAL statement_timeout and assert bounded query result or structured timeout` in `services/backend/tests/performance/test_event_listing_query_plans.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/performance/test_event_listing_query_plans.py -v`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `docs/operations/event-list-performance.md`, document measured figures, index decision and retain offset contract unless separate approved OpenSpec.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/performance/test_event_listing_query_plans.py -v`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

### Task 4: CI checks

**Files:** `services/backend/tests/performance/test_event_listing_query_plans.py; .github/workflows/ci.yml`

**Interfaces:** Consumes the existing component contracts in the OpenSpec design. Produces the behavior asserted by `services/backend/tests/performance/test_event_listing_query_plans.py`.

- [ ] **Step 1 — RED:** Add `test_representative_filter_combinations_match_reference: reuse FILTERS semantic oracle` in `services/backend/tests/performance/test_event_listing_query_plans.py`; state the pre-change behavior that violates the assertion.
- [ ] **Step 2 — Verify failure:** `uv run pytest tests/unit tests/integration tests/performance --cov=app --cov-fail-under=80 -q`. Expected: FAIL with the targeted behavior assertion before any production modification.
- [ ] **Step 3 — GREEN:** In `services/backend/tests/performance/test_event_listing_query_plans.py`, do not gate shared CI on hard latency cutoffs; retain plans and results as artifacts.
- [ ] **Step 4 — Verify green:** `uv run pytest tests/unit tests/integration tests/performance --cov=app --cov-fail-under=80 -q`. Expected: PASS, zero unexpected skips.
- [ ] **Step 5 — Regression:** `cd services/backend && uv run pytest tests/unit tests/integration tests/performance -q`. Expected: PASS; no unauthorized skips.
- [ ] **Step 6 — Commit:** Stage only these files; commit one cohesive functional change in the issue branch.

## Final Verification and Review

- [ ] Run Ruff (`cd services/backend && uv run ruff check .`) and OpenSpec validation.
- [ ] Run CI integration, unit, PostgreSQL RLS, performance and migration workflows for latest SHA.
- [ ] Report exact test totals and measured backend coverage >=80%; no inference from older commits.
- [ ] Request a fresh Codex review, fix blocking findings, and record unresolved operational gates.
- [ ] Mark PR ready only after all checks pass; do not auto-merge.

## Decisions requiring operator evidence

Do not invent benchmark numbers. Record PostgreSQL version, actual EXPLAIN output, query times, index choices and offset/timeout decision.
