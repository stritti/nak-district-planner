## Context

The planner already manages district and congregation events with draft/published states and service assignments. Congregations often have recurring standard service times, but draft events are currently prepared manually. The new capability must generate draft worship events 8 weeks ahead for each congregation, keep generation idempotent, and leave leader assignment empty so planning teams can assign later.

Constraints:
- Existing architecture is hexagonal (domain/application separated from adapters).
- Background processing is done with Celery.
- Event consistency and no-duplicate behavior are required.

## Goals / Non-Goals

**Goals:**
- Automatically pre-generate worship service events for the next 8 weeks from congregation standard times.
- Persist generated events as `DRAFT` with no `ServiceAssignment`.
- Make generation idempotent across repeated runs.
- Support periodic execution through background jobs.

**Non-Goals:**
- Automatic assignment of service leaders.
- Replacing external calendar ingestion workflows.
- Introducing congregation-specific exception logic (holidays/special overrides) in this change.

## Decisions

- Use a dedicated application use case (`GenerateDraftServicesUseCase`) that accepts congregation standard schedules and a generation horizon of 8 weeks.
  - Rationale: Keeps business rules in application/domain layer and independent of FastAPI/Celery/DB adapters.
  - Alternative considered: Implement logic directly in Celery task; rejected because it couples scheduling concerns with domain logic.

- Model generation as deterministic time-slot expansion (from standard weekday/time rules into concrete datetimes within `[today, today+8w)`).
  - Rationale: Deterministic expansion makes behavior testable and reruns predictable.
  - Alternative considered: Store precomputed future templates in DB; rejected due to extra migration and synchronization complexity.

- Enforce idempotency with uniqueness checks on congregation + category + start/end (or equivalent stable slot key) before insert.
  - Rationale: Prevents duplicate draft events during retries and periodic runs.
  - Alternative considered: Hash table for generated slots; rejected for MVP due to additional persistence and lifecycle handling.

- Persist a stable generation-slot identity on created events (for example `generation_slot_key`) and keep it unchanged when event date/time is manually moved.
  - Rationale: A moved generated service still represents the same planned slot, so future generation runs must treat that slot as already fulfilled and must not recreate the original weekday/time entry.
  - Alternative considered: infer moves only from start/end history; rejected because history tracking is not guaranteed in MVP.

- Trigger generation as scheduled Celery task (e.g., daily) and allow safe manual re-trigger.
  - Rationale: Daily cadence keeps 8-week window filled while tolerating task failures.
  - Alternative considered: Generate only on congregation config updates; rejected because outages or missed updates could create planning gaps.

## Risks / Trade-offs

- Timezone/DST boundary errors could shift generated service times -> Mitigation: Use timezone-aware datetime handling and add test cases around DST transitions.
- Strict dedup keys may skip legitimate manually adjusted draft events -> Mitigation: Document key strategy and prefer slot identity based on planned start/end plus congregation/category.
- If slot identity is not persisted, moved events can be regenerated at original standard times -> Mitigation: store immutable `generation_slot_key` and check existence by slot key, not only current datetime.
- Daily background generation increases DB reads/writes -> Mitigation: Query only the required horizon and use batched inserts where possible.
- Missing/invalid standard service-time configuration could produce no events -> Mitigation: Validate schedule configuration and emit operational logs/metrics for skipped congregations.
