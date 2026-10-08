## 1. Domain
- [x] 1.1 Add `PlanningSlot.is_visible_to`, `is_confirmed`, `is_distributed_to` with unit tests
- [x] 1.2 Add `ExportToken.confirmed_only` (PUBLIC forced, INTERNAL honours parameter) with unit tests

## 2. Matrix (UC-03)
- [x] 2.1 Regression test: CANCELLED slot does not render as LÜCKE
- [x] 2.2 Regression test: cancelled earlier slot does not hide active later slot and its assignment
- [x] 2.3 Regression test: district slot only in applicable congregation rows
- [x] 2.4 Filter ACTIVE slots and select cell slot via `is_visible_to`

## 3. Event view (UC-04)
- [x] 3.1 Regression test: PLANNED district slot not distributed
- [x] 3.2 Use `is_distributed_to` for district slots in congregation view

## 4. ICS export (UC-05)
- [x] 4.1 Regression tests: congregation feed, PUBLIC override, STATUS:CANCELLED, change metadata, leader feed
- [x] 4.2 Apply shared predicate and token approval policy in export router
- [x] 4.3 Emit DTSTAMP/LAST-MODIFIED/SEQUENCE from `updated_at`
- [x] 4.4 Include displayed leader and congregation revisions; SEQUENCE based on 2020 (32-bit safe beyond 2038)
- [x] 4.5 Leaders RLS: export tokens read only the leaders their feed names (migration `20261008_rls_export_leaders`); PUBLIC feeds load no leader rows
- [x] 4.6 PUBLIC feeds omit events with INTERNAL visibility

## 5. Frontend
- [x] 5.1 Show approval filter toggle only for INTERNAL export tokens

## 6. Holidays
- [x] 6.1 Regression test: imported holiday distributed to a congregation appears in its event view
- [x] 6.2 Create imported holidays as CONFIRMED; data migration for existing holiday slots
- [x] 6.3 Imported holidays get `applicability=["all"]` (also for existing district holidays in the data migration)
