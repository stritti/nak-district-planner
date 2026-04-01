## Why

The current event model conflates planning structure, execution state, and synchronization behavior, making it difficult to support a normative district planning matrix and controlled bidirectional calendar sync. We need a clear separation between planned structure (Soll) and actual execution (Ist), along with explicit governance over external calendar changes.

## What Changes

- Introduce a series-capable planning model with `PlanningSeries` and `PlanningSlot`.
- Separate execution state into `EventInstance` to support Soll/Ist deviation tracking.
- Define explicit field-level sync authority (STRUCTURAL, SOFT, CONDITIONAL).
- Treat external time changes as deviations rather than structural mutations.
- Introduce governed ingestion of externally created events via `ExternalEventCandidate`.
- Add persistent in-app notifications for externally detected new events.
- Enforce symmetric deletion policy (internal ↔ external).

## Capabilities

### New Capabilities
- `planning-model`: Normative planning structure with PlanningSeries, PlanningSlot, and Soll/Ist separation.
- `hybrid-calendar-sync`: Field-authoritative bidirectional sync with deviation handling.
- `external-event-ingestion`: Review-based ingestion of externally created events with controlled mapping.
- `in-app-notifications`: Persistent in-app notification system for governance-relevant events.
- `matrix-deviation-display`: Matrix rendering based on planning slots with visible time deviations.

### Modified Capabilities

None.

## Impact

- Backend domain model and database schema (new aggregates and tables).
- Sync engine logic and conflict handling.
- Matrix API and frontend rendering.
- Introduction of notification storage and API endpoints.
- Migration from existing monolithic event model to PlanningSlot-based model.
