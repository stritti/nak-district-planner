## 1. Persistence and domain
- [x] 1.1 Add scoped duty category/configuration/override/assignment models with separate partial uniqueness for linked users and name-only normalized names plus transactional duty-capacity locks; do not modify service-leader uniqueness.
- [x] 1.2 Add an additive Alembic migration, idempotent defaults (Gottesdienst: Schließdienst, Organist, Dirigent; others: Schließdienst) and downgrade/legacy data tests.
- [x] 1.3 Implement deterministic inherited configuration resolution, category lifecycle and historical assignment preservation.

## 2. APIs and permissions
- [x] 2.1 Add district and congregation catalogue/configuration read/write APIs with existing membership and RLS checks.
- [x] 2.2 Add event duty assignment CRUD and batch reads; validate event category, district/person references and capacity.
- [x] 2.3 Test unknown/foreign references, scope escalation, disabled categories, duplicates, concurrent updates and missing EventInstance.
- [x] 2.4 Test slot category/congregation changes retaining and flagging now-ineligible existing duties, with no implicit duty deletion; quarantine prior-congregation identities until dual-scope revalidation and verify no privacy leak in views/feeds.
- [x] 2.5 Test capacity reduction below existing assignee count, over-capacity flags and rejection of further assignments.

## 3. Frontend
- [x] 3.1 Add district/congregation configuration screens with effective/inherited/overridden state.
- [x] 3.2 Add optional per-event duty assignment controls and display, including empty, loading, failure and access-denied states.
- [x] 3.3 Add accessible controls and tests for default/non-default event categories, reassignment and multiple duties.

## 4. Personal calendars and iCalendar
- [x] 4.1 Include duty-only assignments in authenticated personal event lists and private personal ICS; aggregate multiple roles into one event.
- [x] 4.2 Keep UID stable, apply cancellation and timing updates, and ensure public feeds never disclose duty-person data.
- [x] 4.3 Test assignment add/remove, dual leader+duty roles, token privacy, distributed slots and absence of EventInstance.
- [x] 4.4 Implement and test subject-bound district-scoped INTERNAL personal tokens, issuance/revocation, cross-subject rejection, lost membership while token remains valid, stale role changes and RLS; preserve legacy leader token semantics.
- [x] 4.5 Test authenticated duty-only personal calendars without leader records, and refusal of unlinked/forged identities.

## 5. Verification
- [x] 5.1 Run OpenSpec validation and reconcile impacted canonical specs before implementation merge.
- [x] 5.2 Run focused backend/frontend tests, Alembic migration and lint/security checks.
- [x] 5.3 Maintain >80% test coverage with explicit error-path and tenant-isolation regressions; document CI outcomes.

## 6. Remembered organisational duty names
- [x] 6.1 Add tenant-scoped, category-scoped autocomplete records with normalised uniqueness, active/suppressed state and persisted historical name snapshots.
- [x] 6.2 Enable validated free-text names as optional duty assignees without requiring a linked account; save/reuse suggestions for the selected duty type.
- [x] 6.3 Implement authorised suggestion management and soft removal, avoiding cross-tenant exposure and automatic resurrection.
- [x] 6.4 Test case/whitespace deduplication, type isolation, deletion/re-entry, historical views, race conditions and no personal calendar access for unlinked names.
- [x] 6.5 Use `duty-name-suggestions` as the only OpenSpec capability for suggestions; enforce scoped `PLANNER` suppression/restoration and reject viewers.
- [x] 6.6 Test exact owning-congregation/district suggestion isolation even when duty definitions are inherited.

## 7. Minister lifecycle and planning
- [x] 7.1 Reuse existing `leaders.is_active` unchanged (including inactive records); migrate only nullable inclusive `service_end_date` and `hidden_from_lists` (default false), and verify no reactivation on migration.
- [x] 7.2 Implement authorised deactivate/reactivate and hide/restore controls; retain all historical references and audit changes.
- [x] 7.3 Filter normal minister pickers/lists and enforce eligibility in event, matrix, bulk and other service assignment writes based on active state and target event date.
- [x] 7.4 Flag existing appointments beyond a newly set end date, without silently deleting assignments.
- [x] 7.5 Test before/on/after end date, role/tenant errors, hidden historical references, stale clients, timezone boundaries, typed former-leader names and migrated data, preserving >80% coverage.
