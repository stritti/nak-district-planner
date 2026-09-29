## Why

PR #375 hardens calendar synchronization, but the current transition functions and flat field-authority map will become increasingly difficult to evolve when conflict resolution, per-integration policies, and additional provider states are added. The architecture already defines PlanningSlot as the aggregate root and requires deterministic, idempotent synchronization. The state policy must make these invariants explicit instead of spreading them across application-service branches.

## What Changes

- Introduce a dedicated domain-level synchronization policy/state-machine abstraction.
- Namespace field authority by aggregate/entity instead of one flat string map.
- Make changed-field classification precede conflict-state transitions.
- Route state changes through PlanningSlot aggregate operations; repositories must not become an alternate mutation path for EventInstance.
- Define explicit conflict-resolution transitions and invalid-transition behavior.
- Preserve provider-neutral domain semantics; no Google/Microsoft/CalDAV concepts enter the domain state machine.

## Capabilities

### New Capabilities
- `sync-state-policy`: declarative, validated sync transitions and conflict resolution.
- `typed-field-authority`: entity-scoped authority classification and external-change decisions.

### Modified Capabilities
- `field-authority-classification`
- `deviation-detection-and-storage`

## Impact

- Domain sync policy and aggregate APIs.
- Application sync orchestration.
- Focused unit/property tests for transitions and field classifications.
- No database migration is required unless implementation discovers persisted state that cannot be represented by the existing SyncState enum.

## Dependencies

- Behavioral baseline: PR #375 / hybrid calendar sync hardening.
- Must remain consistent with `openspec/architecture/overview.md` and `planning-slot-hybrid-sync`.
