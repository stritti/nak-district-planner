## 1. Persistence and domain
- [ ] 1.1 Add scoped duty category/configuration/override/assignment models, constraints and indexes without modifying service-leader uniqueness.
- [ ] 1.2 Add an additive Alembic migration, idempotent defaults (Gottesdienst: Schließdienst, Organist, Dirigent; others: Schließdienst) and downgrade/legacy data tests.
- [ ] 1.3 Implement deterministic inherited configuration resolution, category lifecycle and historical assignment preservation.

## 2. APIs and permissions
- [ ] 2.1 Add district and congregation catalogue/configuration read/write APIs with existing membership and RLS checks.
- [ ] 2.2 Add event duty assignment CRUD and batch reads; validate event category, district/person references and capacity.
- [ ] 2.3 Test unknown/foreign references, scope escalation, disabled categories, duplicates, concurrent updates and missing EventInstance.

## 3. Frontend
- [ ] 3.1 Add district/congregation configuration screens with effective/inherited/overridden state.
- [ ] 3.2 Add optional per-event duty assignment controls and display, including empty, loading, failure and access-denied states.
- [ ] 3.3 Add accessible controls and tests for default/non-default event categories, reassignment and multiple duties.

## 4. Personal calendars and iCalendar
- [ ] 4.1 Include duty-only assignments in authenticated personal event lists and private personal ICS; aggregate multiple roles into one event.
- [ ] 4.2 Keep UID stable, apply cancellation and timing updates, and ensure public feeds never disclose duty-person data.
- [ ] 4.3 Test assignment add/remove, dual leader+duty roles, token privacy, distributed slots and absence of EventInstance.

## 5. Verification
- [ ] 5.1 Run OpenSpec validation and reconcile impacted canonical specs before implementation merge.
- [ ] 5.2 Run focused backend/frontend tests, Alembic migration and lint/security checks.
- [ ] 5.3 Maintain >80% test coverage with explicit error-path and tenant-isolation regressions; document CI outcomes.
