## Context

The existing sync engine uses last-writer-wins semantics for all fields. This causes governance instability: external calendar changes to service time shift the matrix (Soll) position. The `planning-slot-hybrid-sync` change introduced `PlanningSlot` (Soll) and `EventInstance` (Ist) separation, but the sync engine still needs explicit field-level authority rules to leverage this separation.

The current sync pipeline processes external calendar data and writes directly to the event model. After this change, it will classify each incoming field and route it appropriately.

## Goals / Non-Goals

**Goals:**
- Define field-level authority: STRUCTURAL, SOFT, CONDITIONAL
- External structural field changes are ignored
- External time changes update EventInstance with deviation_flag=true
- Deletions propagate bidirectionally

**Non-Goals:**
- Field-level authority UI for administrators (code-defined only)
- External origin tracking beyond deviation storage
- Batch operation handling

## Decisions

### 1. Field Classification

| Field | Authority | Rationale |
|---|---|---|
| `PlanningSlot.congregation_id` | STRUCTURAL | Congregation defines matrix position |
| `PlanningSlot.planning_date` | STRUCTURAL | Date defines matrix row |
| `PlanningSlot.planning_time` | SOFT → CONDITIONAL | Time change stored as deviation |
| `EventInstance.title` | SOFT | External title changes accepted |
| `EventInstance.description` | SOFT | External description changes accepted |
| `PlanningSlot.category` | STRUCTURAL | Category defines service type |

**Decision:** Classification is code-defined (enum + mapping table), not admin-configurable. Keeps sync behavior predictable.

### 2. Deviation Handling Flow

```mermaid
External sync ──▶ Field classifier
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
       STRUCTURAL   SOFT     CONDITIONAL
          │          │          │
          ▼          ▼          ▼
       Ignored    Update     Store in
                   field    EventInstance
                            deviation_flag=true
```

**Decision:** CONDITIONAL (time) updates only `EventInstance.actual_start/actual_end` and sets `deviation_flag = true`. The `PlanningSlot.planning_time` remains unchanged.

### 3. Symmetric Deletion

- External deletion → soft-delete `PlanningSlot` + `EventInstance`
- Internal deletion → push deletion to external calendar (via existing `CalendarConnector`)
- Both sides mark as `cancelled` rather than hard-deleting

**Decision:** Soft-delete with `cancelled` status. Hard deletion would break audit trail and external sync references.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **Classification mismatch** — future field additions not classified | Default to STRUCTURAL for unclassified fields (safe default) |
| **Deviation accumulation** — repeated external time changes create churn | Store only latest deviation, not history |
| **Deletion loops** — internal deletion triggers external deletion which triggers internal again | Track deletion origin; ignore deletions initiated by self |
