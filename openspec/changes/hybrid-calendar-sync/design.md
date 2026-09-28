## Context

PlanningSlot represents the authoritative planned position; EventInstance represents actual/external execution data. Hybrid sync must preserve that separation across edits, deviations, and deletion semantics of different providers.

## Goals / Non-Goals

**Goals:**
- Preserve structural planning authority.
- Merge safe external changes without unnecessary conflicts.
- Represent both start and end/duration deviations.
- Make deviation resolution bidirectional.
- Detect provider deletions whether explicit or represented by absence from an authoritative snapshot.
- Keep delete behavior configurable per integration and idempotent.

**Non-Goals:**
- Admin-configurable field authority.
- CRDT merging.
- Inferring deletions from incomplete provider responses.

## Decisions

### 1. Field Classification and Conflict Scope

| Field | Authority | Behavior |
|---|---|---|
| `PlanningSlot.congregation_id` | STRUCTURAL | External mutation rejected |
| `PlanningSlot.planning_date` | STRUCTURAL | External mutation rejected |
| `PlanningSlot.planning_time` | CONDITIONAL | External time represented on EventInstance |
| `EventInstance.title` | SOFT | External update mergeable |
| `EventInstance.description` | SOFT | External update mergeable |
| `PlanningSlot.category` | STRUCTURAL | External mutation rejected |

Unclassified fields default to STRUCTURAL.

The engine first computes which fields actually changed, then classifies them. DIRTY_INTERNAL alone is insufficient to declare CONFLICT. Non-overlapping SOFT changes may merge; conflicting/authority-violating concurrent changes enter CONFLICT.

### 2. Deviation Semantics

A deviation is present when actual start or actual end/duration differs materially from the planned event.

External time changes update only EventInstance actual times. PlanningSlot remains authoritative.

Resolving a deviation is a command, not merely a flag reset:
1. derive intended corrected actual start/end from PlanningSlot and planned duration rules;
2. transition through internal state-machine semantics;
3. for writable linked integrations, call the connector update operation;
4. persist provider revision/hash;
5. clear deviation and return CLEAN only when the outbound correction is acknowledged.

Read-only integrations may resolve only the internal representation and must expose that external reconciliation was not possible.

### 3. Symmetric Deletion and Reconciliation

Deletion has two normalized inbound forms:
- explicit provider tombstone/cancelled event;
- absence from a complete authoritative provider snapshot.

Google tombstones may lack timestamps and must be parsed by id/status first.

Microsoft/CalDAV-style missing resources require post-fetch reconciliation against active ExternalEventLinks. Absence is deletion only for a complete authoritative scope.

Internal deletion is pushed to writable providers. Self-originated delete echoes are ignored using durable link metadata.

### 4. Delete Policy

Delete behavior is stored per CalendarIntegration:
- `MARK_CANCELLED`: retain planning entities and mark cancelled.
- `HARD_DELETE`: remove eligible internal planning data but retain a minimal ExternalEventLink tombstone.

A process-level default is allowed only as a creation default.

A retained link is a deletion tombstone only after an explicit synchronization transition marks it as such. `event_instance_id = NULL` alone has no tombstone semantics. Domain-driven EventInstance deletion outside calendar synchronization must clean up the link or explicitly delegate to the synchronization deletion workflow.

### 5. Partial Failures

Per-event connector failures are normalized to CalendarConnectorError and do not abort sibling events.

Sync results distinguish `skipped` from `failed`. A partial failure remains visible through API/worker results and integration error metadata.

### 6. Idempotency

Identical active payloads and identical cancellation tombstones are no-ops. No-op processing must not update timestamps merely because the provider repeats the same tombstone.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| False missing-resource deletion | Require authoritative complete reconciliation scope |
| Deletion loops | Durable origin/revision tombstones |
| False conflicts | Diff and classify before state transition |
| Hidden partial failure | Dedicated failed result and error summary |
| Policy inconsistency | Persist delete policy on each integration |
