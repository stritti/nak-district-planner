## 1. Domain Model

- [x] 1.1 Implement PlanningSeries entity
- [x] 1.2 Implement PlanningSlot entity as aggregate root
- [x] 1.3 Refactor existing Event into EventInstance
- [x] 1.4 Move ServiceAssignment ownership to PlanningSlot
- [ ] 1.5 Implement ExternalEventCandidate entity (🔴 CRITICAL - Confirmed missing)
- [ ] 1.6 Implement ExternalEventLink entity (🔴 CRITICAL - Confirmed missing)
- [ ] 1.7 Implement SyncState enum and state machine (🔴 CRITICAL)
- [ ] 1.8 Implement Notification entity (🟠 HIGH)
- [ ] 1.9 Implement FieldAuthority enum (STRUCTURAL, SOFT, CONDITIONAL) (🔴 CRITICAL)

## 2. Persistence Layer

- [x] 2.1 Create migration for planning_series table
- [x] 2.2 Create migration for planning_slots table
- [x] 2.3 Create migration for event_instances table
- [x] 2.4 Consolidate schema for fresh installs without legacy migration flags or backfill
- [ ] 2.5 Create migration for external_event_candidates table (🔴 CRITICAL)
- [ ] 2.6 Create migration for external_event_links table (🔴 CRITICAL)
- [ ] 2.7 Create migration for notifications table (🟠 HIGH)
- [ ] 2.8 Add list_all() and list_by_district() to PlanningSeriesRepository (🔴 CRITICAL - Confirmed gap)

## 3. Application Services

- [ ] 3.1 Implement PlanningSeries slot generation service (🔴 CRITICAL - Confirmed gap)
- [ ] 3.2 Implement ExternalEventCandidate review workflow (🔴 CRITICAL)
- [ ] 3.3 Implement field-level authority enforcer in sync_service.py (🔴 CRITICAL)
- [ ] 3.4 Implement SyncState state machine (🔴 CRITICAL)
- [ ] 3.5 Implement Notification service (🟠 HIGH)
- [ ] 3.6 Implement auto-matching logic for exact slots (🟠 HIGH)
- [ ] 3.7 Refactor sync_service.py to use ExternalEventCandidate workflow (🔴 CRITICAL)

## 4. API Layer

- [x] 4.1 Extend matrix endpoint to include deviation data
- [ ] 4.2 Create notifications API endpoints (list, mark as read, dismiss) (🟠 HIGH)
- [ ] 4.3 Create external events API endpoints for candidate review (🔴 CRITICAL)
- [ ] 4.4 Add RBAC guards to auth.py router (🔴 CRITICAL)
- [ ] 4.5 Add RBAC guards to system.py router (🔴 CRITICAL)

## 5. Frontend

- [ ] 5.1 Update matrix UI to display planned and actual time (🟠 HIGH - Backend provides data)
- [ ] 5.2 Add visual deviation indicators to matrix (colors, icons, tooltips) (🟠 HIGH)
- [ ] 5.3 Implement NotificationBell component (🟠 HIGH)
- [ ] 5.4 Implement NotificationList component (🟠 HIGH)
- [ ] 5.5 Implement Toast system for user feedback (🟠 HIGH)
- [ ] 5.6 Add ConfirmationDialog component for destructive actions (🟠 HIGH)

## 6. Migration & Cleanup

- [ ] 6.1 Migrate matrix rendering to use PlanningSlot ONLY (remove Event fallback) (🔴 CRITICAL - Confirmed: migration incomplete)
- [ ] 6.2 Add feature flag for governed ingestion (USE_GOVERNED_INGESTION)
- [ ] 6.3 Create migration plan from direct sync to candidate workflow
