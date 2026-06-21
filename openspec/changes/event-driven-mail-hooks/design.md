## Context

The `configurable-email-reminders` change (designed in parallel) introduces a MailService port with SMTP/Log/Mock adapters and a daily Celery beat task for scheduled reminders. That handles **time-driven** mail (day-of-month). However, critical planning events happen **asynchronously** — a LÜCKE is detected during a sync, a new external event arrives, a sync job fails. These need **event-driven** notification.

The existing system has several places where domain events naturally occur:
- Calendar sync creates/updates ExternalEventCandidate records
- Slot assignment changes in the matrix view
- Leader registration/confirmation flows
- Sync jobs that can succeed or fail

Each of these sites currently has no mechanism to trigger outbound communication.

## Goals / Non-Goals

**Goals:**
- Define a lightweight, in-process event bus (`DomainEventBus`) for emitting and subscribing to domain events
- Create a generic `EventMailHook` entity that maps an event type to a mail notification (per district, configurable)
- Pre-define initial event types: `SLOT_UNASSIGNED`, `EXTERNAL_EVENT_DETECTED`, `SYNC_ERROR`, `REGISTRATION_RECEIVED`, `ASSIGNMENT_CONFIRMED`, `PLAN_FINALIZED`
- Implement a hook evaluator that receives emitted events and dispatches matching email notifications via the existing MailService
- Add REST API CRUD endpoints for event mail hooks per district
- Add admin UI for hook configuration
- Instrument existing services to emit domain events at the appropriate points

**Non-Goals:**
- Cross-service event bus / message queue (RabbitMQ, Redis Pub/Sub) — in-process event bus is sufficient for MVP
- Webhook delivery (POST to external URL) — mail only for now
- Custom event types defined at runtime via admin UI — event types are code-defined
- Rate limiting / debouncing of events — each event triggers at most one notification per matching hook
- Asynchronous hook evaluation — hook dispatcher runs synchronously within the request/response lifecycle (Celery tasks are already async; service-level events should be fast)

## Decisions

### 1. Domain Event Bus — In-Process Observer Pattern

```mermaid
┌─────────────────────────────────────────────────────────────┐
│                    DomainEventBus                             │
│                                                              │
│  + emit(event: DomainEvent)                                  │
│  + subscribe(event_type, handler)                            │
│                                                              │
│  Internal: dict[EventType → list[callable]]                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │Hook      │ │Future    │ │Future    │
   │Evaluator │ │Handlers  │ │Handlers  │
   └──────────┘ └──────────┘ └──────────┘
```

**Decision:** Use a simple in-process `DomainEventBus` singleton. Services call `event_bus.emit(DomainEvent(type=..., payload=...))`. The `HookEvaluator` subscribes to all event types and checks active `EventMailHook` records against the emitted event type.

**Alternative considered:** Dedicated message queue (Redis Pub/Sub, RabbitMQ) — rejected because:
- All services are in the same process (single Python backend)
- Adding a message queue adds operational complexity for no benefit at this scale
- Can be upgraded later if needed (the `DomainEventBus` interface would remain the same)

**Alternative considered:** Global signal framework (Blinker, Django Signals) — rejected to keep zero external dependencies. A 50-line event bus class is sufficient.

### 2. EventMailHook Domain Model

```text
EventMailHook
──────────────────────
  id: UUID
  district_id: UUID (FK → district)
  event_type: str (e.g. "SLOT_UNASSIGNED")
  recipient_role: str (e.g. "PLANNER")
  subject_template: str (with event-specific placeholders)
  body_template: str (with event-specific placeholders)
  is_active: bool
  created_at: datetime
  updated_at: datetime
```

**Decision:** One record per (district × event_type × recipient_role). A district can have multiple hooks for the same event type targeting different roles (e.g., SLOT_UNASSIGNED → PLANNER and SLOT_UNASSIGNED → ADMIN).

**Placeholders per event type:**

| Event Type | Available Placeholders |
|---|---|
| `SLOT_UNASSIGNED` | `{district_name}, {congregation_name}, {date}, {event_title}` |
| `EXTERNAL_EVENT_DETECTED` | `{district_name}, {event_title}, {event_date}, {source}` |
| `SYNC_ERROR` | `{district_name}, {integration_name}, {error_message}, {timestamp}` |
| `REGISTRATION_RECEIVED` | `{district_name}, {leader_name}, {leader_email}` |
| `ASSIGNMENT_CONFIRMED` | `{district_name}, {leader_name}, {event_title}, {event_date}` |
| `PLAN_FINALIZED` | `{district_name}, {month}, {year}` |

### 3. Hook Evaluator — Subscribes to All Events

```mermaid
Event emitted ──▶ HookEvaluator.on_event(event)
                       │
                       ▼
                ┌─────────────────────┐
                │ Query active hooks   │
                │ WHERE event_type AND │
                │ district_id IN       │
                │ (event's districts)  │
                └──────────┬──────────┘
                           │
                    ┌──────▼──────┐
                    │ For each    │
                    │ matching    │
                    │ hook:       │
                    └──────┬──────┘
                           │
               ┌───────────┴────────────┐
               ▼                        ▼
        ┌────────────────┐     ┌────────────────┐
        │ Resolve role →  │     │ Render template │
        │ user emails     │     │ + app footer    │
        └────────┬───────┘     └────────┬───────┘
                 │                      │
                 └──────────┬───────────┘
                            ▼
                    ┌────────────────┐
                    │ MailService    │
                    │ .send()        │
                    └────────────────┘
```

**Decision:** The `HookEvaluator` is a plain class registered with the `DomainEventBus` during app startup. It receives ALL events, filters by active hooks, and dispatches. No database polling — purely reactive.

**Thread safety:** The event bus and hook evaluator are synchronous and run in the same process. No locking needed for the initial implementation.

### 4. Event Emission Points — Where to Instrument Existing Services

| Service / Operation | Event Type | When to Emit |
|---|---|---|
| Calendar sync (ingestion task) → LÜCKE detection | `SLOT_UNASSIGNED` | After sync, when a `PlanningSlot` of category `Gottesdienst` has no `ServiceAssignment` |
| Calendar sync → ExternalEventCandidate created | `EXTERNAL_EVENT_DETECTED` | After storing a new `ExternalEventCandidate` (not on update) |
| Calendar sync job completion | `SYNC_ERROR` | On sync failure / exception |
| Leader registration approval | `REGISTRATION_RECEIVED` | When a leader registration is approved (or auto-approved) |
| ServiceAssignment confirmation | `ASSIGNMENT_CONFIRMED` | When a leader confirms their assignment (status → CONFIRMED) |
| Plan finalization action | `PLAN_FINALIZED` | When a district plan is explicitly finalized/released by an admin |

**Decision:** Each emission point is a single call: `event_bus.emit(DomainEvent(type=..., payload={...}))`. The payload is a dict with the placeholders and a `district_id` for routing. This keeps instrumentation minimal and non-invasive.

### 5. Event Payload Contract

```python
@dataclass
class DomainEvent:
    event_type: str              # "SLOT_UNASSIGNED"
    district_id: UUID            # routing key
    payload: dict[str, Any]      # placeholder values + metadata
    occurred_at: datetime        # auto-set on creation
```

The `district_id` is required — all hooks are per-district, so without a district the event cannot be matched.

### 6. Recipient Resolution

**Decision:** Identical approach to `configurable-email-reminders` — resolve recipients at dispatch time by querying `Membership` for the target district + role. The `User.email` field is used as the recipient address.

### 7. API Layer

```http
GET    /api/v1/districts/{district_id}/event-hooks
POST   /api/v1/districts/{district_id}/event-hooks
PUT    /api/v1/districts/{district_id}/event-hooks/{hook_id}
DELETE /api/v1/districts/{district_id}/event-hooks/{hook_id}
```

Same pattern as reminder config endpoints. Soft-delete via `is_active=false`.

**Decision:** Reuse the same pattern and router structure as `DistrictReminderConfig` endpoints. This keeps the API consistent.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **Event loop / recursion** — a mail send could trigger another event, causing infinite loop | Ensure no mail-send event is ever emitted. Hook evaluator explicitly does not emit events. |
| **Sync task flooding** — a sync with many LÜCKEs emits many `SLOT_UNASSIGNED` events | Acceptable for MVP — each LÜCKE is a separate legitimate notification. Future: add coalescing (one mail per district summarising all LÜCKEs). |
| **Performance** — hook evaluator queries DB synchronously for each event | Hook evaluator queries are simple indexed lookups (event_type + district_id × is_active). Expected to be fast (<5ms per event). |
| **Stale hooks** — disabled hook still has events emitted for it | Hook evaluator filters `is_active=true`. Emission is fire-and-forget; evaluator silently ignores unmatchable events. |
| **Dependency coupling** — this change depends on `configurable-email-reminders` being implemented first | Enforce via implementation order. The MailService ABC is the only dependency; this change adds no new external dependencies. |

## Open Questions

- Should events be logged/persisted for audit trail? → Useful but deferred; initial version emits events in-memory only.
- Should there be a dry-run/preview endpoint for event hooks? → Useful for admins to test templates without triggering real sends. Deferred.
- Should `SYNC_ERROR` notify the integration owner specifically, or all planners in the district? → All planners initially; the integration-specific `EXTERNAL_EVENT_DETECTED` notification is for the relevant admin.
