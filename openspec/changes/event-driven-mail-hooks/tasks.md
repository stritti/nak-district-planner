## 1. Domain Event Infrastructure

- [x] 1.1 Implement `DomainEvent` dataclass in `app/domain/events/` with fields: event_type, district_id, payload, occurred_at *(`app/domain/events.py`)*
- [x] 1.2 Implement in-process `DomainEventBus` singleton with `emit()` and `subscribe()` methods
- [x] 1.3 Wire `DomainEventBus` into the application startup lifecycle *(`register_event_mail_hooks()` im FastAPI-Lifespan und über Celerys `worker_init`)*

## 2. EventMailHook Domain Model

- [x] 2.1 Implement `EventMailHook` entity in `app/domain/models/` with fields: id, district_id, event_type, subject_template, body_template, recipient_role, is_active, created_at, updated_at *(`recipient_role` als `Role`-Enum validiert)*
- [x] 2.2 Define `EVENT_TYPES` enum/constant list with all 6 pre-defined event types
- [x] 2.3 Implement event-type-specific placeholder map (which placeholders are valid per event type)

## 3. Persistence Layer

- [x] 3.1 Create Alembic migration for `event_mail_hook` table *(`20260930_event_hooks` mit RLS; `20260930_merge_heads` führt die parallelen Heads von #376/#378 zusammen)*
- [x] 3.2 Implement SQLAlchemy ORM model for `EventMailHookORM`
- [x] 3.3 Implement `SqlEventMailHookRepository` with CRUD methods

## 4. Hook Evaluator & Dispatcher

- [x] 4.1 Implement `HookEvaluator` that subscribes to all event types on the DomainEventBus *(`EventMailHookDispatcher` in `app/application/event_mail_hooks.py`)*
- [x] 4.2 Implement event-to-hook matching logic (query active hooks WHERE event_type AND district_id)
- [x] 4.3 Implement recipient resolution via Membership query (same pattern as `configurable-email-reminders`) *(`SqlRecipientDirectory`, gleiche Regel wie Reminder)*
- [x] 4.4 Implement template rendering with event-type-specific placeholder substitution *(Betreff einzeilig gegen Header-Injection)*
- [x] 4.5 Integrate with MailService (call `send()` after rendering) *(ein Versand pro Empfänger; at-most-once wie Reminder)*
- [x] 4.6 Ensure HookEvaluator never emits events itself (guard against infinite loops) *(Dispatcher hat keinen Bus-Zugriff; Test sichert ab)*
- [x] 4.7 Register HookEvaluator with DomainEventBus during application startup

## 5. Event Emission Points

- [x] 5.1 Emit `SLOT_UNASSIGNED` event from LÜCKE detection point (sync/matrix service) *(täglicher Scan `scan_slot_gaps` statt Emission beim Lesen der Matrix; Deduplizierung pro fachlicher Lücke über den Ledger `slot_gap_alerts`, eine geschlossene und wieder geöffnete Lücke wird erneut gemeldet — siehe design.md)*
- [x] 5.2 Emit `EXTERNAL_EVENT_DETECTED` event from ExternalEventCandidate creation
- [ ] 5.3 Emit `SYNC_ERROR` event from calendar sync job on failure *(offen: gehört in `SyncIntegrationTask.on_failure` aus PR #399, um nicht bei jedem Retry zu mailen; nach dessen Merge nachziehen)*
- [x] 5.4 Emit `REGISTRATION_RECEIVED` event from leader registration approval
- [x] 5.5 Emit `ASSIGNMENT_CONFIRMED` event from ServiceAssignment confirmation *(nur beim Übergang nach CONFIRMED)*
- [x] 5.6 Emit `PLAN_FINALIZED` event from plan finalization action *(Freigabe eines ganzen Bezirksmonats über `bulk-approval-status`)*

## 6. API Layer

- [x] 6.1 Create `EventMailHook` Pydantic schemas (Create, Update, Response with event_type validation)
- [x] 6.2 Implement `GET /api/v1/districts/{district_id}/event-hooks` endpoint
- [x] 6.3 Implement `POST /api/v1/districts/{district_id}/event-hooks` endpoint
- [x] 6.4 Implement `PUT /api/v1/districts/{district_id}/event-hooks/{hook_id}` endpoint
- [x] 6.5 Implement `DELETE /api/v1/districts/{district_id}/event-hooks/{hook_id}` endpoint (soft-delete) *(Deaktivierung über `is_active=false`)*
- [x] 6.6 Protect all endpoints with RBAC permission checks (district admin or global admin) *(DISTRICT_ADMIN oder Superadmin; zusätzlich `GET …/event-hooks/event-types` für den Editor)*

## 7. Frontend

- [x] 7.1 Add API client methods for event hook CRUD in `app/api/eventHooks.ts` *(`src/api/eventHooks.ts`)*
- [x] 7.2 Add Pinia store for event hook configuration state *(`src/stores/eventHooks.ts`, verwirft Antworten nach Bezirkswechsel)*
- [x] 7.3 Add event hooks configuration section to district settings view *(`EventHooksPanel` auf `/admin/reminders` neben den monatlichen Erinnerungen)*
- [x] 7.4 Implement event hook form (event type dropdown, role select, subject/body template inputs) *(Platzhalter-Hinweis je Ereignistyp aus `GET …/event-types`; Ereignistyp beim Bearbeiten unveränderlich)*
- [x] 7.5 Implement event hook list with enable/disable toggle per hook

## 8. Tests

- [x] 8.1 Unit tests for `DomainEventBus` (emit/subscribe, multiple subscribers)
- [x] 8.2 Unit tests for `EventMailHook` domain model
- [x] 8.3 Unit tests for template rendering with all event type placeholders
- [x] 8.4 Unit tests for HookEvaluator matching logic (active/inactive/unknown event/unknown district)
- [x] 8.5 Unit tests for HookEvaluator not emitting events
- [x] 8.6 Unit tests for event hook API endpoints
- [x] 8.7 Integration tests for full event → hook → mail flow *(`tests/integration/test_event_mail_hook_flow.py`, läuft in CI gegen PostgreSQL)*
