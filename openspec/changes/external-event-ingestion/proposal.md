## Why

When an external calendar creates a new event that has no corresponding PlanningSlot, the system currently has no mechanism to handle it. Blindly creating a PlanningSlot would bypass governance. Instead, a review workflow is needed: create an `ExternalEventCandidate`, notify administrators, and let them decide whether to map it to an existing slot, create a new slot, or ignore it.

## What Changes

- Introduce `ExternalEventCandidate` entity for review-based ingestion of externally detected events
- Implement auto-matching: if an external event matches an existing PlanningSlot exactly (congregation, date, time, category), it is mapped automatically without creating a candidate
- Add review workflow: list candidates, accept (create mapping or PlanningSlot), or dismiss

## Capabilities

### New Capabilities
- `candidate-creation`: When an external event is detected with no existing mapping, create an ExternalEventCandidate
- `auto-mapping`: Automatically map external events to existing PlanningSlots on exact match (congregation, date, time, category)
- `candidate-review-workflow`: List, accept, or dismiss external event candidates

### Modified Capabilities
- *(none – purely additive)*

## Impact

- **Domain Model** — New `ExternalEventCandidate` entity
- **Database** — New migration for `external_event_candidates` table
- **Sync Engine** — Detection logic triggers candidate creation or auto-mapping
- **API** — New endpoints for candidate listing, acceptance, and dismissal
- **Frontend** — Candidate review modal/UI