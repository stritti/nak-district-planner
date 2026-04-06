## Context

The current event model mixes planning structure, execution time, and sync metadata in a single entity. The matrix view implicitly depends on event datetime, and sync behavior is not explicitly governed by field-level authority. We are introducing a planning-first model with Soll/Ist separation, hybrid sync rules, governed external ingestion, and persistent in-app notifications.

## Goals / Non-Goals

**Goals:**
- Establish `PlanningSeries` and `PlanningSlot` as normative planning structures.
- Separate execution state into `EventInstance` for deviation tracking.
- Implement explicit field-authoritative hybrid sync.
- Introduce review-based ingestion for external new events.
- Add persistent in-app notifications.
- Keep rollout simple for pre-production environments and avoid mandatory historical data migration.

**Non-Goals:**
- Full RRULE support.
- Advanced conflict resolution UI.
- RBAC redesign.
- Multi-tenant isolation redesign.

## Decisions

### 1. PlanningSlot as Aggregate Root
`PlanningSlot` is the aggregate root because:
- The matrix renders slots.
- Service assignments belong to the planned service.
- Sync operates at the concrete instance level.
`PlanningSeries` acts as a template only.

### 2. Soll/Ist Separation
`PlanningSlot` defines planning_date and planning_time (Soll).
`EventInstance` stores actual_start/end (Ist) and deviation flags.
External time changes update only EventInstance.

Alternative considered: Single event with dual timestamps → rejected due to unclear aggregate boundaries.

### 3. Field-Level Sync Authority
Fields are classified as STRUCTURAL, SOFT, or CONDITIONAL.
- STRUCTURAL: never externally mutable.
- SOFT: externally mutable.
- CONDITIONAL (time): stored as deviation.

Alternative considered: last-writer-wins → rejected due to governance instability.

### 4. External Event Ingestion
New external events create `ExternalEventCandidate`.
No automatic PlanningSlot creation except for exact matches.
Governance decision required via review workflow.

### 5. Notification System
Persistent `Notification` entity with read/dismiss semantics.
Visible to district admin and affected congregation admin.
No email delivery.

### 6. Series Generation Strategy
PlanningSeries generates PlanningSlots rolling 6–12 months ahead.
Generation occurs via background job or on-demand expansion.
External changes never mutate series.

## Risks / Trade-offs

[Model Complexity] → Clear aggregate boundaries and phased implementation.
[Coexistence Complexity] → Run the new model alongside legacy events until native write paths are complete.
[Sync Edge Cases] → Strict structural authority to prevent drift.
[Notification Noise] → Auto-matching exact matches to reduce false alerts.

## Rollout Plan

1. Introduce new tables alongside the existing event model.
2. Dual-write newly created or edited events into `PlanningSlot` + `EventInstance`.
3. Switch matrix reads to `PlanningSlot` once enough planning data exists for the target environment.
4. Add an optional one-off import only if old development data must be preserved.
5. Deprecate the old event structure after native write paths are complete.

Rollback: keep the legacy `events` table active until the new write paths are fully adopted.

## Open Questions

- Exact heuristic for detecting Gottesdienst category.
- Retention policy for notifications.
- Handling extreme date deviations if they occur.
