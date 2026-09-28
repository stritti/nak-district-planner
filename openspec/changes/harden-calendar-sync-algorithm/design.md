## Context

The system synchronizes internal planning with external calendar providers. Providers do not expose identical semantics: Google can return cancellation tombstones without timestamps, while collection-style Microsoft Graph and CalDAV reads can make a deleted resource disappear completely. A sync algorithm that only iterates returned events cannot detect all deletions.

The engine must also distinguish a normal no-op from a failed per-event operation. Field authority must be evaluated before declaring conflicts, otherwise harmless external description changes can block internally edited events.

## Goals / Non-Goals

**Goals:**
- Deterministic and idempotent synchronization.
- Field-aware state transitions and conflict detection.
- Detection of explicit cancellation tombstones and resources missing from authoritative provider snapshots.
- Bidirectional time-deviation resolution.
- Integration-specific deletion policy.
- Per-event failure isolation with visible failure reporting.
- Durable update/delete loop prevention.

**Non-Goals:**
- CRDT or arbitrary multi-master merging.
- Guessing deletion from incomplete/non-authoritative result sets.
- Provider-specific behavior leaking into domain policy.

## Decisions

### 1. Field-aware sync state machine

EventInstance uses `CLEAN | DIRTY_INTERNAL | DIRTY_EXTERNAL | CONFLICT`.

The engine SHALL compute the changed field set and classify each changed field before choosing a state transition.

- External SOFT-only changes MAY merge while the instance is DIRTY_INTERNAL.
- CONDITIONAL time changes SHALL be stored as actual-time deviations and SHALL NOT move the PlanningSlot.
- A conflict SHALL be raised only when concurrent changes overlap or violate authority rules.
- STRUCTURAL external changes SHALL never mutate internal planning structure.
- Conflict resolution SHALL use the same state-machine transition functions as normal internal edits; it SHALL NOT silently downgrade CONFLICT by direct assignment.

### 2. Idempotency and acknowledgement

ExternalEventLink stores provider identity, external event id, last acknowledged content hash, revision marker, and durable deletion/tombstone state.

- An already acknowledged unchanged event is a no-op.
- An already acknowledged cancellation is a no-op and SHALL NOT cause recurring writes.
- The stored hash/revision is advanced only after the corresponding inbound change is safely applied or deliberately acknowledged.
- Self-originated outbound revisions/deletions are recognized and ignored on re-entry.

### 3. Provider deletion normalization

Connectors SHALL normalize provider deletion signals into a deletion-capable representation before requiring ordinary event fields.

Google cancellation tombstones MAY contain only provider id/status. Their parsing SHALL NOT require start/end timestamps.

For providers where deleted resources disappear from an authoritative collection response, the sync engine SHALL reconcile the fetched identity set against previously active ExternalEventLinks for that integration.

A missing linked event is considered deleted only when:
1. the fetch represents a complete/authoritative reconciliation scope, and
2. the link was previously active in that scope.

Partial pages, failed fetches, incremental responses without deletion guarantees, or narrowed time windows SHALL NOT be used to infer deletion.

### 4. Reconciliation algorithm

Each successful authoritative snapshot produces a set of seen external ids.

After inbound event processing:
1. load active ExternalEventLinks for the integration and reconciliation scope;
2. compare them with the seen-id set;
3. convert missing links into normalized external deletion operations;
4. apply the integration's delete policy;
5. persist a durable tombstone/revision marker so subsequent runs are idempotent.

Reconciliation failures are per-event failures and SHALL NOT invalidate successfully processed sibling events.

### 5. Bidirectional deviation resolution

A deviation exists when actual start **or actual end/duration** differs materially from the planned values.

Resolving a deviation SHALL:
- restore EventInstance actual times to the intended planned values;
- mark the change as an internal outbound change through the state machine;
- push the corrected times through a connector update operation when the event is externally linked and the integration is writable;
- store the resulting provider revision/hash and return to CLEAN after acknowledgement.

If outbound correction fails, the instance remains retryable and the API SHALL NOT report the deviation as fully synchronized.

### 6. Integration-specific deletion policy

`delete_behavior: MARK_CANCELLED | HARD_DELETE` belongs to CalendarIntegration, not process-global settings.

- MARK_CANCELLED preserves planning/audit entities and marks them cancelled.
- HARD_DELETE removes the internal planning entity where permitted while preserving the ExternalEventLink tombstone needed for loop prevention.
- HARD_DELETE SHALL update audit timestamps on the retained tombstone.
- A deployment-level default MAY initialize new integrations but SHALL NOT override an integration's persisted policy.

### 7. Connector error contract

All expected provider/transport failures from per-event operations, including `httpx.RequestError`, credential validation failures, HTTP failures, and provider concurrency errors, SHALL be translated to `CalendarConnectorError`.

Programming errors are not swallowed by the per-event isolation boundary.

### 8. Partial-failure observability

SyncResult SHALL distinguish:
- created
- updated
- cancelled
- auto_matched
- skipped (valid no-op)
- failed (operation attempted but not completed)

The HTTP sync response and background-job result SHALL expose `failed`.

If one or more per-event operations fail, the integration SHALL retain a bounded operational error summary instead of clearing `last_sync_error`. Successful events remain committed according to the transaction strategy.

Logs SHALL not include unsanitized provider-controlled values.

### 9. Auto-match invariant

If a PlanningSlot matches an external event but has no EventInstance, the sync SHALL create/attach the missing EventInstance to that existing PlanningSlot. It SHALL NOT create a duplicate PlanningSlot.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| False deletion from incomplete fetch | Reconcile only authoritative complete scopes |
| Provider differences | Normalize deletion/update semantics in connector boundary |
| Persistent tombstones | Retain minimal mapping metadata for correctness |
| More state transitions | Centralize transition logic and exhaustively test |
| Partial success ambiguity | Dedicated failed counter and integration error summary |

## Migration Plan

1. Persist delete_behavior on CalendarIntegration with current default.
2. Extend connector contract for update/delete normalization and reconciliation metadata.
3. Add repository query for active links by integration/scope.
4. Implement provider tombstone parsing and authoritative snapshot reconciliation.
5. Make deviation resolution outbound-capable.
6. Extend result schemas/worker payloads with failed count.
7. Add provider and state-machine regression tests.
