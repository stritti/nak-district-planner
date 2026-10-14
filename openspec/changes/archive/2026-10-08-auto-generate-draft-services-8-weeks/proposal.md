## Why

Gemeinden planen Gottesdienste oft mit festen Standardzeiten, aber das manuelle Vorausanlegen kostet Zeit und fuehrt leicht zu Luecken in der Planung. Durch automatische Entwurfsanlage fuer die naechsten 8 Wochen wird die operative Planung fruehzeitig vorbereitet und der Dienstleiter kann spaeter gezielt zugewiesen werden.

## What Changes

- Add a scheduling capability that creates draft worship events 8 weeks in advance based on each congregation's configured standard service times.
- Ensure generated events are created as `DRAFT` and intentionally contain no `ServiceAssignment` / no assigned leader.
- Add idempotent generation logic so reruns do not create duplicate draft events for the same congregation/time slot.
- Define trigger behavior for generation (regular background run) and conflict handling when events already exist.
- Preserve manually shifted generated services so the original standard slot is not re-created after a date move (for example Wednesday service moved to Thursday for Christi Himmelfahrt).

## Capabilities

### New Capabilities
- `draft-service-pre-generation`: Automatic pre-generation of 8 weeks of draft service events from congregation standard service times.

### Modified Capabilities
- (none)

## Impact

- Backend domain/application logic for event generation and idempotency checks.
- Database access layer for querying existing events and persisting new draft events.
- Celery background scheduling/task flow for periodic pre-generation runs.
- Potential API surface for managing congregation standard service times if not already present.
