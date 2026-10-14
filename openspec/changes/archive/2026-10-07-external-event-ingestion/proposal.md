## Why

When an external calendar creates a new event that has no corresponding PlanningSlot, the system currently has no mechanism to handle it. Blindly creating a PlanningSlot would bypass governance. Instead, a review workflow is needed: create an `ExternalEventCandidate`, notify administrators, and let them decide whether to map it to an existing slot, create a new slot, or ignore it.

## What Changes

- Introduce `ExternalEventCandidate` entity for review-based ingestion of externally detected events
- Implement governance-safe auto-matching to existing `PlanningSlot` entries
- Add backend review workflow: list candidates, accept (create mapping or PlanningSlot), or dismiss
- Keep one problematic external event isolated so it cannot abort processing of later events in the same sync run
- Use explicit domain errors and shared external-event mapping logic to keep sync and manual review behavior consistent

## Capabilities

### New Capabilities
- `candidate-creation`: When an external event is detected with no existing mapping, create an ExternalEventCandidate
- `auto-mapping`: Automatically map external events to existing PlanningSlots on exact congregation/date/time match and compatible category semantics
- `candidate-review-workflow`: Backend API to list, accept, or dismiss external event candidates

### Modified Capabilities
- *(none - purely additive)*

## Scope

This PR implements the governed ingestion workflow in the backend only. A frontend review page, Pinia store, API client integration, and notification route are explicitly outside this change and require a separate OpenSpec change.

## Impact

- **Domain Model** - New `ExternalEventCandidate` entity and explicit review errors
- **Database** - New migration for `external_event_candidates` table
- **Sync Engine** - Detection logic triggers candidate creation or auto-mapping without aborting the run for an unassignable slot
- **Application Layer** - Shared mapping logic for automatic and reviewed assignments
- **API** - New endpoints for candidate listing, acceptance, and dismissal
- **Observability** - Review-relevant transitions can be logged with structured context
