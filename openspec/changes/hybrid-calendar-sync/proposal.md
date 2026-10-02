## Why

Hybrid calendar sync must preserve internal planning authority while still accepting legitimate external changes. Provider behavior differs for edits and deletions, and deviation resolution must be truly bidirectional rather than merely changing local state.

## What Changes

- Define STRUCTURAL, SOFT, and CONDITIONAL field authority.
- Evaluate the changed field set before conflict transitions.
- Treat start and end/duration changes as deviations without moving PlanningSlot.
- Resolve deviations by synchronizing corrected times back to writable providers.
- Normalize explicit deletion tombstones and reconcile resources missing from authoritative snapshots.
- Apply deletion policy per CalendarIntegration.
- Distinguish normal skips from failed per-event operations.

## Capabilities

### New Capabilities
- `field-authority-classification`
- `deviation-detection-and-storage`
- `symmetric-deletion`
- `provider-reconciliation`
- `partial-sync-observability`

### Modified Capabilities
- `calendar-sync-algorithm`: field-aware conflict and reconciliation semantics.

## Impact

- Domain sync policy and EventInstance state transitions.
- Calendar connector update/delete contracts.
- CalendarIntegration configuration.
- ExternalEventLink reconciliation queries and tombstones.
- API/worker sync result schemas.
