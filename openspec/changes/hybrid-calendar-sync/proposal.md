## Why

The current calendar sync treats all fields equally and uses last-writer-wins semantics. This causes instability: an external calendar change to a service time overwrites the planned (Soll) time, shifting the matrix position. The sync engine needs explicit field-level authority rules to distinguish structural fields (never externally mutable) from soft fields and time changes (stored as deviations).

## What Changes

- Define explicit field-level sync authority: STRUCTURAL (never externally mutable), SOFT (externally mutable), CONDITIONAL (time → stored as deviation)
- Implement deviation handling: external datetime changes update `EventInstance` and set `deviation_flag = true` instead of mutating `PlanningSlot`
- Enforce symmetric deletion: deletions propagate bidirectionally between internal and external systems

## Capabilities

### New Capabilities
- `field-authority-classification`: Defines which fields are STRUCTURAL, SOFT, or CONDITIONAL and enforces these rules during sync
- `deviation-detection-and-storage`: Detects external time changes, stores them in EventInstance, and marks deviatio
- `symmetric-deletion`: Propagates deletions bidirectionally between internal and external calendars

### Modified Capabilities
- *(none – purely additive)*

## Impact

- **Sync Engine** — Classification logic in the sync pipeline; deviation storage in EventInstance; deletion propagation
- **Domain Models** — Uses existing PlanningSlot, EventInstance, and ExternalEvent entities (no new entities)
- **API** — Potential extension to expose deviation data (already partially in matrix endpoint)
