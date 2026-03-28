## Context

The system uses hybrid bidirectional synchronization between internal planning and external calendar providers. Without a formally defined state machine and deterministic algorithm, the system risks duplication, update loops, inconsistent deletion behavior, and silent structural corruption.

## Goals / Non-Goals

**Goals:**
- Define explicit sync states and transitions.
- Guarantee idempotent processing.
- Prevent update loops.
- Separate structural conflict handling from soft-field merging.
- Provide deterministic delete behavior.

**Non-Goals:**
- Full CRDT-based conflict resolution.
- Distributed multi-master reconciliation.

## Decisions

### 1. Sync State Machine

EventInstance SHALL contain:
- sync_state: CLEAN | DIRTY_INTERNAL | DIRTY_EXTERNAL | CONFLICT
- last_synced_hash
- last_external_modified_at
- last_internal_modified_at

Transitions:

- Internal change → DIRTY_INTERNAL
- External change → DIRTY_EXTERNAL
- Successful sync → CLEAN
- Structural conflict → CONFLICT

### 2. Idempotency Strategy

Each external event is mapped via ExternalEventLink containing:
- provider
- external_event_id
- internal_event_id
- last_synced_hash

Incoming external payload hash is compared to stored hash to avoid duplicate updates.

### 3. Loop Prevention

Each outbound push stores a provider-specific revision marker.
If a subsequent inbound webhook carries identical revision, update is ignored.

### 4. Conflict Rules

- Structural fields changed externally → ignored and overwritten by internal state.
- Soft fields → merged.
- Concurrent internal + external structural change → CONFLICT state.

### 5. Delete Behavior

Integration configuration includes:
- delete_behavior: MARK_CANCELLED | HARD_DELETE

External delete → handled according to configuration.

### 6. Partial Failure Handling

- Sync processes events individually.
- Failure of one event SHALL NOT abort entire integration sync.
- Failures logged and retried according to retry policy.

## Risks / Trade-offs

[Complexity] → Explicit state machine reduces ambiguity.
[Storage overhead] → Additional metadata per event.
[Edge cases] → Covered via deterministic transitions.

## Migration Plan

1. Add sync metadata fields to EventInstance.
2. Introduce ExternalEventLink table.
3. Refactor sync worker to state-machine-driven logic.
4. Validate via staged integration tests.

Rollback: Feature-flag new sync engine.
