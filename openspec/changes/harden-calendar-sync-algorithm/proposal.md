## Why

The calendar synchronization engine is central to the system’s integrity. As the system evolves toward hybrid governance (planning authority + external integration), the sync algorithm must be formally defined to prevent data loss, infinite loops, drift, and inconsistent state.

## What Changes

- Define a deterministic sync state machine.
- Formalize idempotent event processing using hash + revision metadata.
- Define conflict detection rules for structural vs soft fields.
- Define loop-prevention mechanism for bidirectional sync.
- Define delete behavior configuration (MARK_CANCELLED vs HARD_DELETE).
- Specify retry and partial-failure behavior at algorithm level.

## Capabilities

### New Capabilities
- `calendar-sync-algorithm`: Deterministic, idempotent, and governance-aware synchronization engine.

### Modified Capabilities
- `hybrid-calendar-sync`: Refined conflict detection and loop-prevention semantics.

## Impact

- Sync engine refactor (application layer).
- External mapping persistence structure.
- EventInstance sync metadata expansion.
- Background job orchestration changes.
