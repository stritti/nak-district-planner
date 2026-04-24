# Phase 1 Technical Plan: Planning Model Refactor

This document defines the concrete technical execution plan for Phase 1 of the
implementation roadmap (`planning-slot-hybrid-sync`) for a consolidated
fresh-install baseline.

---

## 1. Phase 1 Goal

Introduce the planning model foundation without rollout flags or historical
migration paths.

In scope:
- `PlanningSeries` (template layer)
- `PlanningSlot` (aggregate root)
- `EventInstance` (actual execution)
- Move `ServiceAssignment` ownership to `planning_slot_id`
- Keep the existing event API surface operational while it persists the
  canonical planning model

Out of scope:
- Hardened sync state machine activation
- RBAC enforcement
- Notification/candidate workflows

---

## 2. Current Baseline (As-Is)

Existing core persistence:
- `events` table with both planning + execution + sync fields
- `service_assignments` references `events.id`
- Matrix endpoint previously read from `events` + `service_assignments`

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
- `default_planning_time` TIME
- `recurrence_pattern` JSONB
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
- `planning_time` TIME not null
- `status` ENUM (`ACTIVE`, `CANCELLED`) not null
- `created_at`, `updated_at`

3. `event_instances`
- `id` UUID PK
- `planning_slot_id` UUID FK planning_slots unique not null
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
- add `planning_slot_id` UUID FK planning_slots
- keep `event_id` only as API compatibility linkage for now

---

## 4. Consolidated Implementation Strategy

### Step A: Schema foundation

Alembic migration:
- Create new enum `planning_slot_status`
- Create `planning_series`, `planning_slots`, `event_instances`
- Add `planning_slot_id` to `service_assignments`
- Add indexes:
  - `ix_planning_slots_district_date`
  - `ix_planning_slots_congregation_date`
  - unique `uq_event_instances_planning_slot_id`

The migration targets fresh installs and does not backfill legacy rows.

### Step B: Canonical writes

Application behavior:
1. Event create/update flows persist into `events`, `planning_slots`, and
   `event_instances`.
2. `service_assignments.planning_slot_id` is populated for every new assignment.
3. No feature flags gate the planning-model write path.

### Step C: Canonical reads

1. Matrix read path uses `planning_slots` + `event_instances` +
   `service_assignments.planning_slot_id`.
2. Existing list/get event endpoints continue serving the current API contract
   while the planning model is already the canonical source for matrix and
   assignment behavior.

---

## 5. Repository and API Shape

### 5.1 New Repositories

Add:
- `PlanningSeriesRepository`
- `PlanningSlotRepository`
- `EventInstanceRepository`

Bridge behavior:
- `EventRepository.save` also persists `PlanningSlot` and `EventInstance`

### 5.2 API Compatibility

Phase 1 keeps external event APIs stable where possible.

Internal translation:
- `EventResponse.start_at/end_at` continues to use event-facing semantics
- Matrix payload uses `PlanningSlot`/`EventInstance` directly
- Assignment ownership is keyed by `planning_slot_id`

---

## 6. Data Validation Checklist

Must pass on a fresh-install deployment:

1. Referential integrity:
- no orphan `event_instances`
- no orphan `service_assignments.planning_slot_id`

2. Canonical write correctness:
- newly created/updated events create matching `planning_slots` and
  `event_instances`

3. Matrix behavior:
- gaps and occupied cells render correctly from `planning_slots`

4. API compatibility:
- existing event and assignment endpoints keep working with the consolidated
  persistence model

---

## 7. Testing Plan

### Unit tests
- domain constructors for `PlanningSeries`, `PlanningSlot`, `EventInstance`
- mapping logic event -> planning model

### Integration tests
- migration creates the new schema for a fresh database
- matrix output with slot-backed data
- assignment CRUD with `planning_slot_id` linkage

### Smoke tests
- create event
- update event
- list matrix
- create assignment

---

## 8. Ownership and Exit Criteria

Phase 1 is complete when:
- New model is live as the default planning path
- Matrix uses slot-based source
- Assignment ownership uses `planning_slot_id`
- Validation checklist passes

---

End of Phase 1 Technical Plan
