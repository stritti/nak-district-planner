## Why

The current event model conflates planning structure with execution state, making it difficult to support a normative district planning matrix. We need a clear separation between planned structure (Soll) and actual execution (Ist), and a series-capable planning model.

## What Changes

- Introduce a series-capable planning model with `PlanningSeries` and `PlanningSlot`.
- Separate execution state into `EventInstance` to support Soll/Ist deviation tracking.
- Matrix view renders from `PlanningSlot` as authoritative source.
- Visible deviation indicators in matrix when planned and actual times differ.

## Capabilities

### New Capabilities
- `planning-model`: Normative planning structure with PlanningSeries, PlanningSlot, EventInstance, and Soll/Ist separation.
- `matrix-deviation-display`: Matrix rendering based on planning slots with visible time deviations.

### Modified Capabilities

None.

## Impact

- Backend domain model and database schema (PlanningSeries, PlanningSlot, EventInstance tables).
- Matrix API rendering based on PlanningSlot.
- Establish the PlanningSlot/EventInstance model as the default planning backbone for fresh
  installations without rollout flags or historical migration requirements.
