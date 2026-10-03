## Why

The current event model conflates planning structure with execution state, making it difficult to support a normative district planning matrix. We need a clear separation between planned structure (Soll) and actual execution (Ist), and a series-capable planning model.

## What Changes

- Introduce a series-capable planning model with `PlanningSeries` and `PlanningSlot`.
- Separate execution state into `EventInstance` to support Soll/Ist deviation tracking.
- Matrix view renders from `PlanningSlot` as authoritative source.
- Visible deviation indicators in matrix when planned and actual times differ.
- Remove the legacy `events` persistence model after migrating existing data; compatibility APIs project from `PlanningSlot` + `EventInstance`.
- Define retention cleanup at the `PlanningSlot` aggregate root so dependent `EventInstance` rows are removed by database cascade without leaving orphans.

## Capabilities

### New Capabilities
- `planning-model`: Normative planning structure with PlanningSeries, PlanningSlot, EventInstance, Soll/Ist separation, and aggregate lifecycle semantics.
- `matrix-deviation-display`: Matrix rendering based on planning slots with visible time deviations.

### Modified Capabilities

None.

## Impact

- Backend domain model and database schema (PlanningSeries, PlanningSlot, EventInstance tables).
- Matrix API rendering based on PlanningSlot.
- Event compatibility endpoints backed by the canonical planning model rather than a legacy `events` table.
- Retention cleanup based on `PlanningSlot.planning_date`, including database-enforced cascade deletion of dependent EventInstances.
- PostgreSQL regression coverage for retention cutoff boundaries and cascade behavior.
