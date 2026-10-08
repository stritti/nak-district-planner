## 1. Domain and Data Foundations

- [x] 1.1 Define/extend congregation standard service-time model and repository port methods needed to read schedules for generation.
- [x] 1.2 Define the slot expansion rules for the rolling 8-week window (weekday/time to concrete timezone-aware datetimes).
- [x] 1.3 Add persistence query support to detect existing matching draft worship events for idempotent generation.
- [x] 1.4 Add a stable generation slot identifier (e.g., `generation_slot_key`) to generated events and keep it immutable when event datetime is changed.

## 2. Application Use Case Implementation

- [x] 2.1 Implement `GenerateDraftServicesUseCase` in the application layer to iterate congregations and compute target slots.
- [x] 2.2 Implement creation of missing events as `DRAFT` with no `ServiceAssignment`.
- [x] 2.3 Implement duplicate-prevention checks so reruns do not create duplicate events for existing slots.
- [x] 2.4 Update generation logic to resolve duplicates via generation slot identity so manually moved generated services block recreation of original standard slots.

## 3. Background Execution and Integration

- [x] 3.1 Add a Celery task/entrypoint that executes the generation use case on a periodic schedule.
- [x] 3.2 Configure scheduling cadence (daily) and safe re-trigger behavior for operational recovery.
- [x] 3.3 Add structured logging/metrics for generated, skipped, and invalid-configuration congregations.

## 4. Verification and Tests

- [x] 4.1 Add unit tests for slot expansion, 8-week horizon boundaries, and no-assignment default behavior.
- [x] 4.2 Add unit/integration tests for idempotency (second run creates no duplicates).
- [x] 4.4 Add test case for moved generated event (Wednesday -> Thursday) to verify no regeneration at the original slot.
- [x] 4.3 Add timezone/DST-focused tests to verify generated datetimes remain stable across transitions.
