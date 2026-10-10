## 1. Persistence and domain
- [ ] 1.1 Add scoped duty category/configuration/override/assignment models, constraints and indexes without modifying service-leader uniqueness.
- [ ] 1.2 Add an additive Alembic migration, idempotent defaults (Gottesdienst: Schließdienst, Organist, Dirigent; others: Schließdienst) and downgrade/legacy data tests.
- [ ] 1.3 Implement deterministic inherited configuration resolution, category lifecycle and historical assignment preservation.

## 2. APIs and permissions
- [ ] 2.1 Add district and congregation catalogue/configuration read/write APIs with existing membership and RLS checks.
- [ ] 2.2 Add event duty assignment CRUD and batch reads; validate event category, district/person references and capacity.
- [ ] 2.3 Test unknown/foreign references, scope escalation, disabled categories, duplicates, concurrent updates and missing EventInstance.
- [ ] 2.4 Test slot category/congregation changes retaining and flagging now-ineligible existing duties, with no implicit duty deletion.
- [ ] 2.5 Test capacity reduction below existing assignee count, over-capacity flags and rejection of further assignments.

## 3. Frontend
- [ ] 3.1 Add district/congregation configuration screens with effective/inherited/overridden state.
- [ ] 3.2 Add optional per-event duty assignment controls and display, including empty, loading, failure and access-denied states.
- [ ] 3.3 Add accessible controls and tests for default/non-default event categories, reassignment and multiple duties.

## 4. Personal calendars and iCalendar
- [ ] 4.1 Include duty-only assignments in authenticated personal event lists and private personal ICS; aggregate multiple roles into one event.
- [ ] 4.2 Keep UID stable, apply cancellation and timing updates, and ensure public feeds never disclose duty-person data.
- [ ] 4.3 Test assignment add/remove, dual leader+duty roles, token privacy, distributed slots and absence of EventInstance.
- [ ] 4.4 Implement and test subject-bound district-scoped INTERNAL personal tokens, issuance/revocation, cross-subject rejection, stale role changes and RLS; preserve legacy leader token semantics.
- [ ] 4.5 Test authenticated duty-only personal calendars without leader records, and refusal of unlinked/forged identities.

## 5. Verification
- [ ] 5.1 Run OpenSpec validation and reconcile impacted canonical specs before implementation merge.
- [ ] 5.2 Run focused backend/frontend tests, Alembic migration and lint/security checks.
- [ ] 5.3 Maintain >80% test coverage with explicit error-path and tenant-isolation regressions; document CI outcomes.

## 6. Remembered organisational duty names
- [ ] 6.1 Add tenant-scoped, category-scoped autocomplete records with normalised uniqueness, active/suppressed state and persisted historical name snapshots.
- [ ] 6.2 Enable validated free-text names as optional duty assignees without requiring a linked account; save/reuse suggestions for the selected duty type.
- [ ] 6.3 Implement authorised suggestion management and soft removal, avoiding cross-tenant exposure and automatic resurrection.
- [ ] 6.4 Test case/whitespace deduplication, type isolation, deletion/re-entry, historical views, race conditions and no personal calendar access for unlinked names.
- [ ] 6.5 Use `duty-name-suggestions` as the only OpenSpec capability for suggestions; enforce scoped `PLANNER` suppression/restoration and reject viewers.
- [ ] 6.6 Test exact owning-congregation/district suggestion isolation even when duty definitions are inherited.

## 7. Minister lifecycle and planning
- [ ] 7.1 Add additive minister active/hidden status and nullable inclusive service end date; backfill existing records as active/visible.
- [ ] 7.2 Implement authorised deactivate/reactivate and hide/restore controls; retain all historical references and audit changes.
- [ ] 7.3 Filter normal minister pickers/lists and enforce eligibility in event, matrix, bulk and other service assignment writes based on active state and target event date.
- [ ] 7.4 Flag existing appointments beyond a newly set end date, without silently deleting assignments.
- [ ] 7.5 Test before/on/after end date, role/tenant errors, hidden historical references, stale clients, timezone boundaries, typed former-leader names and migrated data, preserving >80% coverage.
