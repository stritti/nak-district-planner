## Context

The current implementation uses small transition functions and a flat field-name authority map. That was appropriate for initial hardening, but it does not encode aggregate ownership or legal transition graphs strongly enough for conflict resolution.

## Goals

- One authoritative place for sync transition rules.
- Compile-time/type-level distinction between PlanningSlot and EventInstance field policies where practical.
- Deterministic transitions independent of adapters and persistence.
- No direct external mutation of structural planning data.
- Test every legal and illegal transition.

## Non-Goals

- Replacing repositories or the entire application service.
- Introducing provider SDKs.
- Changing persisted SyncState values without a separate migration decision.

## Design Decisions

1. The state machine belongs to the domain layer and has no HTTP, SQLAlchemy, or provider dependencies.
2. PlanningSlot remains the aggregate root. EventInstance state changes are exposed through aggregate behavior/application commands that validate the aggregate.
3. Field authority is keyed by entity/model and field, not only by field name.
4. External changes are first classified into structural, soft, conditional, or irrelevant changes; only meaningful concurrent changes may create CONFLICT.
5. Conflict resolution is modeled as explicit commands/transitions, not direct state assignment.
6. Prefer an established state-machine library only if it preserves domain purity, typed states, async-independence, and testability. `python-statemachine` and `transitions` must be evaluated in a short ADR-style implementation note before selection. A library is not a goal by itself.
7. Unknown fields fail closed for external mutation and produce structured diagnostics without logging provider-controlled raw text.

## Compatibility and Migration

Existing SyncState values remain the compatibility contract. The implementation must include characterization tests for PR #375 behavior before refactoring. Any semantic change requires an explicit MODIFIED requirement and regression test.

## Testing

- Transition table tests covering every state/event pair.
- Field-authority tests per entity namespace.
- Conflict tests for soft-only, conditional-only, structural, and mixed changes.
- Aggregate-boundary tests proving EventInstance cannot bypass PlanningSlot validation.
- Coverage for the changed domain/application modules must remain at least 80%.
