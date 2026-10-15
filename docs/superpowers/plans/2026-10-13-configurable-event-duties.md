# Configurable Event Duties Implementation Plan

> **For agentic workers:** Use Superpowers TDD and independently scoped implementation and review tasks. Existing merged OpenSpec is the approved design; the user explicitly requested implementation and a PR.

**Goal:** Implement PR #525, including optional event duties, remembered names, private personal calendars and minister lifecycle.

**Architecture:** Retain PlanningSlot as aggregate identity and keep organisational assignments separate from ServiceAssignment. Resolve inherited configuration in pure domain functions, put persistence behind ports, and enforce scoped permissions plus PostgreSQL RLS at adapter boundaries.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy, PostgreSQL, Alembic, Vue 3, TypeScript, Vitest, pytest.

**Spec:** `openspec/changes/configurable-event-duty-assignments/` (proposal, design, all six delta specs).

## Global Constraints

- All assignments optional; defaults Gottesdienst: Schließdienst, Organist, Dirigent; other exact event categories: Schließdienst.
- Names are scoped by owning congregation/district and duty category; never infer account identity from a name.
- Existing historical assignments and inactive leaders remain intact. Quarantine moved-scope private assignments.
- Capacity and duplicate checks must serialize concurrent writes. ServiceAssignment uniqueness unchanged.
- Only verified account subjects can qualify for personal calendars. Public/general INTERNAL feeds contain no private duty data.
- Coverage >80%, negative permission/identity/date tests, additive migration and downgrade checks.

## Review Focus

- Scope changes with same person name: destination readers cannot see quarantined names.
- Capacity reductions and concurrent final-place writes: retain old rows but reject excess new rows.
- Revoked membership and stale personal tokens: fail closed on every request.
- Inactive minister entered as free text or saved from a stale picker: reject all write paths.
- Cancelled/missing-instance slots and multiple duties: one stable calendar UID with current timing/status.

## Task 1: Duties backend and persistence

**Files:** New `domain/models/event_duty.py`, `domain/ports/event_duties.py`, `application/event_duties.py`, `adapters/db/orm_models/event_duty.py`, `adapters/db/repositories/event_duties.py`, `adapters/api/schemas/event_duty.py`, `adapters/api/routers/event_duties.py`, and related unit/integration tests, all under `services/backend/app` or `services/backend/tests`.

**Interfaces:** Provide scoped configuration/catalogue, assignment CRUD/batch, suggestions, eligible linked-user choices and explicit dual-scope revalidation. Expose immutable assignment `display_name`, `duty_label`, `linked_user_sub`, `district_id`, `congregation_id`, `planning_slot_id`; persist assignment original scope. Coordinate endpoint contracts before frontend integration. Root owns combined Alembic migration and registration.

- [x] Write and run failing tests for exact defaults, overrides, disabled duties, capacities, identity exclusivity, normalisation and privacy quarantine.
- [x] Implement domain/ports and persistence, transactional locks, validation and scoped router.
- [x] Add negative permission, unknown/foreign references, duplicate/suppressed suggestions and changed-scope regression tests.
- [x] Verify focused tests and coverage; review task before integration.

## Task 2: Minister lifecycle

**Files:** Existing leader domain/ORM/repository/schema/router, service assignment conflict/write validation, relevant frontend leader administration/pickers, and new lifecycle tests. Root owns migration, audit registration and shared event response integration.

**Interfaces:** Add `hidden_from_lists: bool = False`, `service_end_date: date | None = None`; preserve `is_active`. Provide authoritative eligibility and future assignment review flags. Administrative `include_inactive` access must be scoped.

- [x] Test before/on/after inclusive date, hidden/inactive state and normalised typed-name bypass.
- [x] Implement fields and permission-checked lifecycle writes, selectors, and all assignment write-path validation.
- [x] Preserve privileged historical resolution and flag future invalid appointments without deleting them.
- [x] Verify tests and >80% focused coverage, then review task.

## Task 3: Personal calendars, migration and RLS

**Files:** Export token domain/ORM/repository/schema/router, new personal calendar router/projection, combined Alembic migration, DB RLS helpers, ORM/router/audit registration, PostgreSQL integration tests.

**Interfaces:** `subject_sub` binds INTERNAL token to existing User and one district. Ownership/admin management and current membership checks apply on every request. Subject calendar merges securely linked leader entries and duty entries by slot ID, using existing event timing/status projection.

- [x] Test forged/cross-subject/public-token rejection and revoked membership.
- [x] Implement subject-bound personal event list and ICS projection without changing existing feed semantics.
- [x] Implement additive migration, idempotent seeding for existing/new districts and scoped RLS.
- [x] Verify missing-instance, changed timing, cancellation, duplicate role merging and migration roundtrip/drift.

## Task 4: Duties frontend

**Files:** New `src/api/eventDuties.ts`, scoped duty settings view, event duties panel, personal calendar view; existing event list, routes/navigation and related tests in `services/frontend`.

**Interfaces:** Consume Task 1 REST contract and Task 3 personal event/token endpoints. Use existing auth/context/API client patterns.

- [x] Test effective/inherited/override state and optional name/account assignment.
- [x] Implement settings, event editor, suggestion hide/restore and private calendar controls.
- [x] Test loading/error/access-denied, duplicate names, reassignment and multiple roles.
- [x] Verify TypeScript build, focused Vitest coverage >80% and lint.

## Task 5: Integration and PR

- [x] Reconcile canonical OpenSpec and task checklist with implemented, verified behavior.
- [ ] Run complete backend/frontend tests, lint, OpenSpec strict validation, migration upgrade/downgrade/drift and relevant PostgreSQL checks.
- [ ] Obtain independent spec/quality review and fix findings.
- [ ] Commit, push feature branch and open PR referencing #525 with concrete test evidence and remaining limitations, if any.
