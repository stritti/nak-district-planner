# Phase 1 Technical Plan: Planning Model Refactor

This document defines the concrete technical execution plan for Phase 1 of the
implementation roadmap (`planning-slot-hybrid-sync`), including schema changes,
data migration, compatibility strategy, validation, and rollback.

---

## 1. Phase 1 Goal

Introduce the new planning model foundation without changing sync behavior yet.

In scope:
- `PlanningSeries` (template layer)
- `PlanningSlot` (aggregate root)
- `EventInstance` (actual execution)
- Move `ServiceAssignment` ownership from `event_id` to `planning_slot_id`
- Backfill existing `events` data into the new model
- Keep legacy APIs operational during transition

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
- backfill from `event_id` mapping
- set `planning_slot_id` NOT NULL (step 2)
- remove `event_id` (step 3, after cutover)

---

## 4. Migration Strategy (Expand -> Backfill -> Contract)

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

### Step B: Backfill (data migration)

Backfill script/migration job:
1. For each row in `events`:
   - create `planning_slots` row:
     - `district_id = events.district_id`
     - `congregation_id = events.congregation_id`
     - `category = events.category`
     - `planning_date = date(events.start_at)`
     - `planning_time = time(events.start_at)`
     - `status = ACTIVE` unless `events.status = CANCELLED`
   - create `event_instances` row:
     - `planning_slot_id = created slot`
     - `title/description` from event
     - `actual_start_at = events.start_at`
     - `actual_end_at = events.end_at`
     - `source`, `visibility`, timestamps from event
     - `deviation_flag = false`
2. Build mapping `event_id -> planning_slot_id` in memory/batch temp table.
3. Backfill `service_assignments.planning_slot_id` using mapping.
4. Validation checks (see section 7).

### Step C: Compatibility Cutover

Introduce feature flag `USE_PLANNING_SLOT_MODEL` in backend config.

Flag OFF (default initially):
- Existing API/repositories keep reading legacy `events` path.

Flag ON:
- Matrix read path uses `planning_slots` + `event_instances` + `service_assignments.planning_slot_id`.
- Event create/update endpoints write to new model (while optional dual-write remains active).

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
- `ENABLE_DUAL_WRITE_EVENTS` (optional safety; default true during transition)

Dual write behavior (if enabled):
- create/update in new model and legacy `events` until cutover confidence is reached.

---

## 7. Data Validation Checklist

Must pass before enabling flag in production:

1. Row count parity:
- `events` count == `planning_slots` count == `event_instances` count

2. Assignment parity:
- count of `service_assignments.event_id` mapped rows == count of non-null `planning_slot_id`

3. Referential integrity:
- no orphan `event_instances`
- no orphan `service_assignments.planning_slot_id`

4. Matrix parity (sample districts):
- same number of gaps and occupied cells before/after cutover

5. API parity:
- list and get endpoints produce equivalent business values

---

## 8. Testing Plan

### Unit tests
- domain constructors for `PlanningSeries`, `PlanningSlot`, `EventInstance`
- mapping logic legacy -> new model

### Integration tests
- migration backfill correctness
- matrix output parity under flag OFF vs ON
- assignment CRUD with planning_slot linkage

### Smoke tests
- create event
- update event
- list matrix
- create assignment

---

## 9. Rollout Plan

1. Deploy migration A (expand)
2. Run backfill in staging
3. Validate parity metrics
4. Deploy app with flag OFF
5. Enable flag ON in staging
6. Validate matrix/API behavior
7. Enable in production for one district (canary)
8. Roll out district by district

---

## 10. Rollback Plan

If major issue appears after flag ON:
- turn `USE_PLANNING_SLOT_MODEL` OFF
- continue serving legacy `events`
- keep new tables for diagnosis

If schema issue before contract migration:
- rollback application only (no destructive DB rollback required)

No destructive table drops until one stable release cycle completes.

---

## 11. Ownership and Exit Criteria

Phase 1 is complete when:
- New model is live behind flag
- Matrix uses slot-based source in production
- Assignment ownership moved to `planning_slot_id`
- Legacy path is no longer required for normal operation
- Validation checklist passes

---

End of Phase 1 Technical Plan
