## Context

When the calendar sync detects an external event that has no corresponding `PlanningSlot`, the current sync engine has no defined behavior. This change introduces a governed ingestion workflow: create an `ExternalEventCandidate`, attempt auto-mapping to existing slots, and provide a review interface for administrators.

The `planning-slot-hybrid-sync` change established `PlanningSlot` as the authoritative planning structure. External events should not create `PlanningSlot` entries without governance approval.

## Goals / Non-Goals

**Goals:**
- Create `ExternalEventCandidate` for unmatched external events
- Auto-map external events to existing `PlanningSlot` on exact match (congregation, date, time, category)
- Provide API endpoints for candidate review (list, accept, dismiss)
- Provide frontend candidate review modal

**Non-Goals:**
- Partial matching (fuzzy date ranges, approximate times)
- Bulk candidate operations
- Candidate expiry/cleanup policy

## Decisions

### 1. ExternalEventCandidate Entity

```
ExternalEventCandidate
──────────────────────
  id: UUID
  district_id: UUID (FK)
  external_event_id: str (UID from source)
  source: str (calendar integration name)
  congregation_id: UUID | null
  event_date: date
  event_time: time | null
  title: str
  category: str | null
  status: PENDING | ACCEPTED | DISMISSED
  matched_slot_id: UUID | null (auto-mapped)
  created_at: datetime
  reviewed_at: datetime | null
  reviewed_by: UUID | null (User ID)
```

**Decision:** Keep candidate as a simple entity with status. When accepted, either link to an existing `PlanningSlot` (via `matched_slot_id`) or create a new one.

### 2. Auto-Mapping Logic

```
External event detected
       │
       ▼
┌─────────────────────────┐
│ Query PlanningSlots     │
│ WHERE congregation =    │
│   event.congregation    │
│   AND date = event.date │
│   AND time = event.time │
│   AND category = cat    │
└─────────┬───────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
  Match     No match
    │           │
    ▼           ▼
  Create     Create
  mapping    Candidate
  (skip      (needs
  candidate)  review)
```

**Decision:** Exact match only (all four fields: congregation, date, time, category). No fuzzy matching for MVP.

### 3. Review Actions

| Action | Effect |
|---|---|
| **Accept & Map** | Link candidate to existing `PlanningSlot`, set status=ACCEPTED, emit event |
| **Accept & Create** | Create new `PlanningSlot` from candidate data, set status=ACCEPTED |
| **Dismiss** | Set status=DISMISSED, no further action |

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **False positives** — auto-mapping matches wrong slot | Exact-match criteria minimize this. Manual review can correct. |
| **Duplicate candidates** — same external event detected in consecutive syncs | Check existing candidates before creating new ones (by external_event_id + source) |
| **Orphaned candidates** — accepted but slot later deleted | Accept writes into PlanningSlot; slot lifecycle is independent after mapping |