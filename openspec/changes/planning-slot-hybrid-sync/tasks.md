## 1. Domain Model

- [x] 1.1 Implement PlanningSeries entity
- [x] 1.2 Implement PlanningSlot entity as aggregate root
- [x] 1.3 Refactor existing Event into EventInstance
- [ ] 1.4 Move ServiceAssignment ownership to PlanningSlot
- [ ] 1.5 Implement ExternalEventCandidate entity
- [ ] 1.6 Implement Notification entity
- [ ] 1.7 Add SyncState enumeration and deviation fields

## 2. Persistence Layer

- [x] 2.1 Create migration for planning_series table
- [x] 2.2 Create migration for planning_slots table
- [x] 2.3 Create migration for event_instances table
- [ ] 2.4 Create migration for external_event_candidates table
- [ ] 2.5 Create migration for notifications table
- [x] 2.6 Implement data migration from legacy events

## 3. Sync Engine

- [ ] 3.1 Implement field-level classification logic
- [ ] 3.2 Implement deviation handling for datetime updates
- [ ] 3.3 Implement symmetric deletion handling
- [ ] 3.4 Implement exact-match auto-mapping logic
- [ ] 3.5 Implement candidate creation workflow

## 4. Application Services

- [ ] 4.1 Implement PlanningSeries slot generation service
- [ ] 4.2 Implement ExternalEventCandidate review use case
- [ ] 4.3 Implement Notification emission service
- [ ] 4.4 Implement mark-as-read and dismiss use cases

## 5. API Layer

- [ ] 5.1 Add endpoint for listing notifications
- [ ] 5.2 Add endpoint for marking notifications as read
- [ ] 5.3 Add endpoint for reviewing external candidates
- [x] 5.4 Extend matrix endpoint to include deviation data

## 6. Frontend

- [ ] 6.1 Add persistent notification badge to dashboard
- [ ] 6.2 Implement notification center view
- [ ] 6.3 Implement candidate review modal
- [ ] 6.4 Update matrix UI to display planned and actual time
