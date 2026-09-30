## Context

When the calendar sync detects an external event that has no corresponding `PlanningSlot`, the sync engine needs a governed fallback. This change introduces `ExternalEventCandidate`, attempts safe auto-mapping to existing slots, and provides a backend review API for administrators.

The `planning-slot-hybrid-sync` change established `PlanningSlot` as the authoritative planning structure. External events must not create `PlanningSlot` entries without governance approval.

## Goals / Non-Goals

**Goals:**
- Create `ExternalEventCandidate` for unmatched external events
- Auto-map external events to an existing `PlanningSlot` when congregation, date and time match and category constraints are compatible
- Keep per-event mapping failures isolated so later events continue to sync
- Provide backend API endpoints for candidate review (list, accept, dismiss)
- Reuse one mapping service for automatic and reviewed assignment
- Use explicit domain errors instead of string-based `ValueError` contracts
- Keep candidate refresh and candidate status transitions separate
- Validate target eligibility and event intervals before updating review status

**Non-Goals:**
- Frontend candidate review UI, route, Pinia store, or API client (separate PR #390)
- Fuzzy matching or approximate time matching
- Bulk candidate operations
- Candidate expiry/cleanup policy
- Introducing a new dependency-injection framework

## Decisions

### 1. ExternalEventCandidate Entity

```text
ExternalEventCandidate
----------------------
  id: UUID
  district_id: UUID (FK)
  calendar_integration_id: UUID (FK)
  external_event_id: str
  source: str
  congregation_id: UUID | null
  title: str
  category: str | null
  start_at: datetime
  end_at: datetime
  description: str | null
  content_hash: str
  status: PENDING | ACCEPTED | DISMISSED
  matched_slot_id: UUID | null
  created_at: datetime
  updated_at: datetime
  reviewed_at: datetime | null
  reviewed_by: str | null
```

While status is PENDING, a new source version updates event data, `content_hash`, and `updated_at` in place. Refreshing data never changes status implicitly. Cancellation is handled explicitly by the sync workflow by dismissing a pending candidate.

### 2. Auto-Mapping Logic

A slot is eligible when:
- district is already scoped by the slot query
- congregation matches exactly
- planning date equals the external event date in UTC
- planning time equals the external event time in UTC
- if the integration defines `default_category`, the slot category is either that category or unset
- if the integration has no default category, category does not block an otherwise exact match

The external event title is content and is never used as an implicit category.

If a matching slot already belongs to another calendar integration or has unresolved local changes, the event is not fatal to the sync run. It remains or becomes a candidate and processing continues with the next event.

### 3. Shared Mapping Service

Automatic mapping and candidate acceptance SHALL use the same application/domain service for:
- creating or updating `EventInstance`
- assigning external identifiers and integration
- setting `sync_state=CLEAN`
- computing deviation against the slot
- creating `ExternalEventLink`
- persisting the source revision marker when available

This prevents semantic drift between automatic and manual review flows.

### 4. Review Actions and Transaction Boundary

| Action | Effect |
|---|---|
| **Accept & Map** | Link candidate to an existing active `PlanningSlot`, set status=ACCEPTED |
| **Accept & Create** | Create a new `PlanningSlot`, map the external event, set status=ACCEPTED |
| **Dismiss** | Set status=DISMISSED, no mapping is created |

Review operations are terminal. Re-reviewing a non-PENDING candidate raises a dedicated domain exception. Accept rejects zero or negative event durations before any writes. When accepting into an existing slot, the service validates district ownership, active status and absence of conflicting mappings or local edits before mapping. When creating a new slot, the service does not query an instance by the newly generated slot ID.

The API locks the candidate row for review and, where an existing target is selected, obtains its advisory lock. Candidate, slot, instance and link changes share one database session/transaction, committed by the session dependency. If a persistence operation fails, the transaction rolls back; the service does not mark an accepted candidate before its mapping writes succeed. A failed mapping leaves the candidate pending on the next transaction.

### 5. Error Semantics

Candidate review uses dedicated exception types such as:
- `CandidateAlreadyReviewedError`
- `CandidateInvalidPeriodError`
- `CandidateSlotNotAssignableError`
- `CandidateSlotAlreadyLinkedError`

The API translates these to HTTP 409. Authorization and not-found behavior remain separate API concerns.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **False positive auto-match** | Exact congregation/date/time matching and conservative category compatibility |
| **Duplicate candidates** | Unique key on integration + external event ID and locked repository lookup |
| **Semantic drift** | One shared mapping service used by sync and review |
| **One bad event blocks sync** | Unassignable slot becomes candidate; sync continues |
| **Hidden state transitions** | Refresh only updates data; dismiss/accept are explicit transitions |
| **Partial mapping on persistence failure** | One database transaction, with review transition after successful mapping writes |
