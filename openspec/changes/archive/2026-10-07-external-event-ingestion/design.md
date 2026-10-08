## Context

When the calendar sync detects an external event that has no corresponding `PlanningSlot`, the sync engine needs a governed fallback. This change introduces `ExternalEventCandidate`, attempts safe auto-mapping to existing slots, and provides a backend review API for administrators.

The `planning-slot-hybrid-sync` change established `PlanningSlot` as the authoritative planning structure. External events must not create `PlanningSlot` entries without governance approval. PR #375 established the authoritative sync state machine, field-level authority, provider acknowledgements, cancellation propagation and durable deletion tombstones. Candidate ingestion must preserve these existing guarantees.

## Goals / Non-Goals

**Goals:**
- Create `ExternalEventCandidate` for unmatched external events
- Auto-map external events to an existing `PlanningSlot` when congregation, date and time match and category constraints are compatible
- Keep per-event mapping and persistence failures isolated so later events continue to sync
- Provide backend API endpoints for candidate review (list, accept, dismiss)
- Reuse one mapping service for automatic and reviewed assignment
- Use explicit domain errors instead of string-based `ValueError` contracts
- Keep candidate refresh and candidate status transitions separate
- Validate target eligibility and event intervals before updating review status
- Preserve provider revision and resource identity so #375's subsequent sync can reconcile accepted events correctly

**Non-Goals:**
- Frontend candidate review UI, route, Pinia store, or API client (separate PR #390)
- Fuzzy matching or approximate time matching
- Bulk candidate operations
- Candidate expiry/cleanup policy
- Introducing a new dependency-injection framework
- Replacing #375's handling of already-linked provider events

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
  revision_marker: str | null
  provider_resource_id: str | null
  status: PENDING | ACCEPTED | DISMISSED
  matched_slot_id: UUID | null
  created_at: datetime
  updated_at: datetime
  reviewed_at: datetime | null
  reviewed_by: str | null
```

While status is PENDING, a new source version updates event data, `content_hash`, provider revision and resource identity, and `updated_at` in place. Refreshing data never changes status implicitly. Cancellation is handled explicitly by the sync workflow by dismissing a pending candidate. Accepted and dismissed decisions remain terminal; a later sync must never automatically re-map or reopen a terminal candidate.

### 2. Auto-Mapping Logic

A slot is eligible when:
- district is already scoped by the slot query
- congregation matches exactly
- planning date equals the external event date in UTC
- planning time equals the external event time in UTC
- the slot is active
- if the integration defines `default_category`, the slot category is either that category or unset
- if the integration has no default category, category does not block an otherwise exact match

The external event title is content and is never used as an implicit category.

If a matching slot already belongs to another calendar integration, already carries a provider link, or has unresolved local changes, the event remains or becomes a candidate and processing continues with the next event. Before claiming a matching slot, acquire a transaction-scoped advisory lock for that slot ID and re-read its occupying instance. Manual review of an existing slot acquires the same lock.

### 3. Shared Mapping Service

Automatic mapping and candidate acceptance SHALL use the same application/domain service for:
- creating or updating `EventInstance`
- assigning external identifiers and integration
- setting `sync_state=CLEAN`
- computing deviation against the slot using the planned start and configured expected duration
- creating `ExternalEventLink`
- preserving the source revision marker and provider resource ID when available
- storing `last_synced_payload` and the acknowledged content hash for #375's field-level conflict reconciliation

This prevents semantic drift between automatic and manual review flows. Existing linked events continue through #375's original state machine; only new, unlinked events enter candidate ingestion.

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

### 6. Sync Failure Isolation and Migration Reconciliation

Each unlinked external event is processed inside its own nested database transaction/savepoint, itself owned by the integration-wide transaction. A failure in candidate creation, notification persistence or mapping rolls back only the affected event, increments the existing failed-event counter and leaves later fetched events eligible for processing. Log static failure context instead of provider-controlled exception messages. Existing linked-event processing retains the #375 state machine and its separate connector-error handling; non-idempotent provider writes are not automatically retried by candidate ingestion.

The migration uses revision `0021`, down-revision `0020` from `0020_sync_policy_state`. It includes the candidate's provider revision and resource identity. A second migration with revision `0020` must never be introduced.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **False positive auto-match** | Exact active-slot congregation/date/time matching and conservative category compatibility |
| **Concurrent slot claims** | Stable advisory lock per slot and occupation check after acquiring that lock |
| **Duplicate candidates** | Unique key on integration + external event ID and locked repository lookup |
| **Semantic drift** | One shared mapping service used by sync and review; preserve #375 payload baselines |
| **One bad event blocks sync** | Per-event savepoint, failed counter, continued processing of later events |
| **Hidden state transitions** | Refresh only updates PENDING data; dismiss/accept are terminal decisions |
| **Partial mapping on persistence failure** | Transactional review and nested sync savepoints, with review transitions after mapping writes |
