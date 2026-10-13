# Recurring Monthly Checklist: PR #570 Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task by task. Each task is test-first and independently verifiable.

**Goal:** Finish issue #557 in the existing PR branch without changing PlanningSeries, loosening CI, or exposing cross-tenant data.

**Architecture:** Follow the approved OpenSpec under `openspec/changes/add-recurring-event-monthly-checklist/`. Domain rules stay pure, application commands depend on ports, PostgreSQL owns uniqueness/RLS, API adapters enforce district and congregation authorization, and the Vue UI only writes on explicit acceptance.

**Tech stack:** Python/FastAPI/SQLAlchemy/PostgreSQL/Alembic/pytest; Vue 3/TypeScript/Vitest/Playwright; OpenSpec.

**Spec:** `openspec/changes/add-recurring-event-monthly-checklist/design.md` and `specs/recurring-event-monthly-planning/spec.md`.

## Global Constraints

- No automatic creation of PlanningSlots or EventInstances by a month preview.
- Reuse the existing PLANNED/CONFIRMED publication semantics.
- Enforce district/congregation scopes before reads and writes; leave RLS enabled.
- Avoid breaking the existing recurring calendar, PlanningSeries, or service generator.
- Keep changed production paths above 80% statement coverage; test failure cases.
- Preserve API idempotency and item-level transaction isolation for bulk accepts.

## Review Focus

- Invalid and stale revisions must yield stable conflict signals and never leak raw DB errors.
- A busy district with many templates must not yield unbounded template-list responses or incorrect `total`.
- Filtering must occur before template pagination, including security scope.
- A deleted accepted slot must not be re-created; subsequent explicit resolution must validate scope/date.
- Client forms must handle partial bulk failures and simultaneous NEEDS_REVIEW rows without sharing values.

---

### Task 1: Stable bulk error contracts (API + UI)

**Files:** `services/backend/app/adapters/api/routers/recurring_events.py`, `services/backend/tests/unit/test_recurring_events_api.py`, `services/frontend/src/views/RecurringEventsView.vue`, `services/frontend/src/views/RecurringEventsView.test.ts`, OpenSpec design.

- [ ] Write regression tests for known conflict, stale template, invalid occurrence, ambiguous/nonexistent local time and unknown ValueError containing private details.
- [ ] Run the test and establish the expected failure.
- [ ] Replace raw exception string exposure with stable error codes, mapped to understandable German UI messages.
- [ ] Confirm backend and frontend tests and whole CI.

### Task 2: Bounded, authorization-filtered template listing

**Files:** recurring template router/repository/schemas/API client/Vue view and tests, OpenSpec.

- [ ] Write tests proving `total` counts visible results and limit/offset apply after visibility and before delivery.
- [ ] Implement bounded GET list pagination and expose navigation in management UI; audit monthly expansion for large template sets.
- [ ] Confirm overflow, unauthorized and empty cases.

### Task 3: UI review fixes and component boundaries

**Files:** `services/frontend/src/views/RecurringEventsView.vue`, extracted checklist/template/preview components, matching tests.

- [ ] Regression-test per-item resolution, form semantics, invalid references, status transitions and mobile states.
- [ ] Correct text input classes; avoid free-form linkage when compatible slots can be selected.
- [ ] Extract focused components without changing observable workflows; preserve existing tests.

### Task 4: Complete feature integration and proof

**Files:** Backend PostgreSQL/RLS tests, browser/E2E tests, OpenSpec tasks, PR description.

- [ ] Test concurrent/duplicate accepts, per-item unique failures, cross-scope access and retention deletion.
- [ ] Verify PUBLIC ICS requires CONFIRMED and existing generator behavior remains unchanged.
- [ ] Run strict OpenSpec validation, Ruff, pytest with coverage, Vitest, browser tests, migration roundtrip, security and all workflows.
- [ ] Mark only evidenced OpenSpec tasks complete, request final code review and make PR ready only after verification.
