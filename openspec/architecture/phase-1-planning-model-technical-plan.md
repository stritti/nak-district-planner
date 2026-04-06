# Phase 1 Technical Plan: Planning Model Refactor

This document defines the concrete technical execution plan for Phase 1 of the
implementation roadmap (`planning-slot-hybrid-sync`), including schema changes,
compatibility strategy, validation, and rollback for a pre-production rollout.

---

## 1. Phase 1 Goal

Introduce the new planning model foundation without changing sync behavior yet.

In scope:
- `PlanningSeries` (template layer)
- `PlanningSlot` (aggregate root)
- `EventInstance` (actual execution)
- Move `ServiceAssignment` ownership from `event_id` to `planning_slot_id`
- Keep legacy APIs operational during transition
- Dual-write newly created or modified events into the new model during transition

Out of scope:
- Hardened sync state machine activation
- RBAC enforcement
- Notification/candidate workflows

---

## 2. Current Baseline (As-Is)

Existing core persistence:
- `events` table with both planning + execution + sync fields
- `service_assignments` references `events.id`
- Matrix endpoint reads from `events` + `service_assignments`

Existing risks:
- Event model is overloaded
- No formal aggregate boundary
- No separation between normative plan and actual execution

---

## 3. Target Data Model (Phase 1 End State)

### 3.1 New Tables

1. `planning_series`
- `id` UUID PK
- `district_id` UUID FK districts
- `congregation_id` UUID FK congregations (nullable)
- `category` VARCHAR(255) nullable
- `default_planning_time` TIME WITH TIME ZONE or TIME (project standard)
- `recurrence_pattern` JSONB (lightweight rule)
- `active_from` DATE nullable
- `active_until` DATE nullable
- `is_active` BOOLEAN not null default true
- `created_at`, `updated_at`

2. `planning_slots`
- `id` UUID PK
- `series_id` UUID FK planning_series nullable
- `district_id` UUID FK districts
- `congregation_id` UUID FK congregations nullable
- `category` VARCHAR(255) nullable
- `planning_date` DATE not null
- `planning_time` TIME WITH TIME ZONE or TIME not null
- `status` ENUM (`ACTIVE`, `CANCELLED`) not null
- `created_at`, `updated_at`

3. `event_instances`
- `id` UUID PK
- `planning_slot_id` UUID FK planning_slots unique not null (Phase 1: 1:1)
- `title` VARCHAR(500) not null
- `description` TEXT nullable
- `actual_start_at` TIMESTAMPTZ not null
- `actual_end_at` TIMESTAMPTZ not null
- `source` existing enum `event_source`
- `visibility` existing enum `event_visibility`
- `deviation_flag` BOOLEAN not null default false
- `created_at`, `updated_at`

### 3.2 Existing Table Changes

`service_assignments`:
- add `planning_slot_id` UUID FK planning_slots nullable (step 1)
- keep `event_id` during transition
- set `planning_slot_id` NOT NULL once native slot writes are complete
- remove `event_id` (step 3, after cutover)

---

## 4. Rollout Strategy (Expand -> Prospective Dual Write -> Contract)

### Step A: Expand (non-breaking)

Alembic migration A:
- Create new enum `planning_slot_status`
- Create `planning_series`, `planning_slots`, `event_instances`
- Add `planning_slot_id` to `service_assignments` (nullable)
- Add indexes:
  - `ix_planning_slots_district_date`
  - `ix_planning_slots_congregation_date`
  - unique `uq_event_instances_planning_slot_id`

No existing read/write path changed.

### Step B: Prospective population (no mandatory backfill)

Application behavior:
1. Leave existing `events` rows untouched.
2. Dual-write new or edited events into `planning_slots` + `event_instances`.
3. Populate `service_assignments.planning_slot_id` for newly created or edited assignments.
4. If old development data must remain visible, add a one-off import script later instead of
   making the migration mandatory.

### Step C: Compatibility Cutover

Introduce feature flag `USE_PLANNING_SLOT_MODEL` in backend config.

Flag OFF (default initially):
- Existing API/repositories keep reading legacy `events` path.

Flag ON:
- Matrix read path uses `planning_slots` + `event_instances` + `service_assignments.planning_slot_id`.
- Event create/update endpoints keep dual-writing while native slot writes are introduced incrementally.

### Step D: Contract (after stabilization)

Alembic migration C (post-verification):
- Set `service_assignments.planning_slot_id` NOT NULL
- Drop `service_assignments.event_id`
- Keep `events` table for one release as rollback buffer OR archive then remove

---

## 5. Repository and API Cutover Plan

### 5.1 New Repositories

Add:
- `PlanningSeriesRepository`
- `PlanningSlotRepository`
- `EventInstanceRepository`

Temporary bridge adapter:
- map legacy `EventRepository` methods onto `planning_slots + event_instances` when flag is ON.

### 5.2 API Compatibility

Phase 1 keeps external API contract stable where possible.

Internal translation:
- `EventResponse.start_at/end_at` served from `EventInstance.actual_*`
- `category`, `district_id`, `congregation_id` served from `PlanningSlot`

Matrix endpoint:
- switch to slot-based source when flag is ON

---

## 6. Feature Flags

Introduce config flags:
- `USE_PLANNING_SLOT_MODEL` (primary cutover)
- `ENABLE_DUAL_WRITE_EVENTS` (default true during transition)

Dual write behavior (if enabled):
- create/update in new model and legacy `events` until cutover confidence is reached.

---

## 7. Data Validation Checklist

Must pass before enabling flag in production:

1. Referential integrity:
- no orphan `event_instances`
- no orphan `service_assignments.planning_slot_id`

2. Dual-write correctness:
- newly created/updated events create matching `planning_slots` and `event_instances`

3. Matrix behavior (sample districts with slot data):
- gaps and occupied cells render correctly from `planning_slots`

4. API compatibility:
- list and get endpoints continue to serve legacy business values until the API contract changes

---

## 8. Testing Plan

### Unit tests
- domain constructors for `PlanningSeries`, `PlanningSlot`, `EventInstance`
- mapping logic legacy -> new model

### Integration tests
- migration creates the new schema without mutating existing `events`
- matrix output under flag ON with slot-backed data
- assignment CRUD with `planning_slot_id` linkage

### Smoke tests
- create event (dual-write enabled)
- update event (dual-write enabled)
- list matrix
- create assignment

---

## 9. Rollout Plan

1. Deploy migration A (expand)
2. Deploy app with `ENABLE_DUAL_WRITE_EVENTS=true` and `USE_PLANNING_SLOT_MODEL=false`
3. Create or edit planning data in the target environment
4. Enable `USE_PLANNING_SLOT_MODEL=true` once the matrix can be served from slot-backed data
5. Introduce native slot writes
6. Remove legacy event reads/writes after stabilization

---

## 10. Rollback Plan

If major issue appears after flag ON:
- turn `USE_PLANNING_SLOT_MODEL` OFF
- continue serving legacy `events`
- keep new tables for diagnosis

If schema issue before contract migration:
- rollback application only (no destructive DB rollback required)

No destructive table drops until the new slot-based write path is the default.

---

## 11. Ownership and Exit Criteria

Phase 1 is complete when:
- New model is live behind flag
- Matrix uses slot-based source in the active environment
- Assignment ownership moved to `planning_slot_id`
- Historical data migration remains optional unless required by a later production rollout
- Validation checklist passes

---

End of Phase 1 Technical Plan
