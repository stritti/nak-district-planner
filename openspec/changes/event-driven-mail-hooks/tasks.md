## 1. Domain Event Infrastructure

- [ ] 1.1 Implement `DomainEvent` dataclass in `app/domain/events/` with fields: event_type, district_id, payload, occurred_at
- [ ] 1.2 Implement in-process `DomainEventBus` singleton with `emit()` and `subscribe()` methods
- [ ] 1.3 Wire `DomainEventBus` into the application startup lifecycle

## 2. EventMailHook Domain Model

- [ ] 2.1 Implement `EventMailHook` entity in `app/domain/models/` with fields: id, district_id, event_type, subject_template, body_template, recipient_role, is_active, created_at, updated_at
- [ ] 2.2 Define `EVENT_TYPES` enum/constant list with all 6 pre-defined event types
- [ ] 2.3 Implement event-type-specific placeholder map (which placeholders are valid per event type)

## 3. Persistence Layer

- [ ] 3.1 Create Alembic migration for `event_mail_hook` table
- [ ] 3.2 Implement SQLAlchemy ORM model for `EventMailHookORM`
- [ ] 3.3 Implement `SqlEventMailHookRepository` with CRUD methods

## 4. Hook Evaluator & Dispatcher

- [ ] 4.1 Implement `HookEvaluator` that subscribes to all event types on the DomainEventBus
- [ ] 4.2 Implement event-to-hook matching logic (query active hooks WHERE event_type AND district_id)
- [ ] 4.3 Implement recipient resolution via Membership query (same pattern as `configurable-email-reminders`)
- [ ] 4.4 Implement template rendering with event-type-specific placeholder substitution
- [ ] 4.5 Integrate with MailService (call `send()` after rendering)
- [ ] 4.6 Ensure HookEvaluator never emits events itself (guard against infinite loops)
- [ ] 4.7 Register HookEvaluator with DomainEventBus during application startup

## 5. Event Emission Points

- [ ] 5.1 Emit `SLOT_UNASSIGNED` event from LÜCKE detection point (sync/matrix service)
- [ ] 5.2 Emit `EXTERNAL_EVENT_DETECTED` event from ExternalEventCandidate creation
- [ ] 5.3 Emit `SYNC_ERROR` event from calendar sync job on failure
- [ ] 5.4 Emit `REGISTRATION_RECEIVED` event from leader registration approval
- [ ] 5.5 Emit `ASSIGNMENT_CONFIRMED` event from ServiceAssignment confirmation
- [ ] 5.6 Emit `PLAN_FINALIZED` event from plan finalization action

## 6. API Layer

- [ ] 6.1 Create `EventMailHook` Pydantic schemas (Create, Update, Response with event_type validation)
- [ ] 6.2 Implement `GET /api/v1/districts/{district_id}/event-hooks` endpoint
- [ ] 6.3 Implement `POST /api/v1/districts/{district_id}/event-hooks` endpoint
- [ ] 6.4 Implement `PUT /api/v1/districts/{district_id}/event-hooks/{hook_id}` endpoint
- [ ] 6.5 Implement `DELETE /api/v1/districts/{district_id}/event-hooks/{hook_id}` endpoint (soft-delete)
- [ ] 6.6 Protect all endpoints with RBAC permission checks (district admin or global admin)

## 7. Frontend

- [ ] 7.1 Add API client methods for event hook CRUD in `app/api/eventHooks.ts`
- [ ] 7.2 Add Pinia store for event hook configuration state
- [ ] 7.3 Add event hooks configuration section to district settings view
- [ ] 7.4 Implement event hook form (event type dropdown, role select, subject/body template inputs)
- [ ] 7.5 Implement event hook list with enable/disable toggle per hook

## 8. Tests

- [ ] 8.1 Unit tests for `DomainEventBus` (emit/subscribe, multiple subscribers)
- [ ] 8.2 Unit tests for `EventMailHook` domain model
- [ ] 8.3 Unit tests for template rendering with all event type placeholders
- [ ] 8.4 Unit tests for HookEvaluator matching logic (active/inactive/unknown event/unknown district)
- [ ] 8.5 Unit tests for HookEvaluator not emitting events
- [ ] 8.6 Unit tests for event hook API endpoints
- [ ] 8.7 Integration tests for full event → hook → mail flow
