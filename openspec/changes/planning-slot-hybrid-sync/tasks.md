## 1. Domain Model

- [x] 1.1 Implement PlanningSeries entity
- [x] 1.2 Implement PlanningSlot entity as aggregate root
- [x] 1.3 Refactor existing Event into EventInstance
- [x] 1.4 Move ServiceAssignment ownership to PlanningSlot

## 2. Persistence Layer

- [x] 2.1 Create migration for planning_series table
- [x] 2.2 Create migration for planning_slots table
- [x] 2.3 Create migration for event_instances table
- [x] 2.4 Consolidate schema for fresh installs without legacy migration flags or backfill

## 3. Application Services

- [ ] 3.1 Implement PlanningSeries slot generation service

## 4. API Layer

- [x] 4.1 Extend matrix endpoint to include deviation data

## 5. Frontend

- [ ] 5.1 Update matrix UI to display planned and actual time
