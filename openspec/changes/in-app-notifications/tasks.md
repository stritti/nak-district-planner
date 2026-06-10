## 1. Domain Model

- [ ] 1.1 Implement `Notification` entity with fields: id, district_id, user_id (nullable), notification_type, title, message, reference_type, reference_id, is_read, is_dismissed, created_at

## 2. Persistence Layer

- [ ] 2.1 Create Alembic migration for `notifications` table
- [ ] 2.2 Implement SQLAlchemy ORM model for `NotificationORM`
- [ ] 2.3 Implement repository with list (filterable, ordered), create, mark-read, mark-dismissed methods

## 3. Notification Emission

- [ ] 3.1 Implement notification creation service
- [ ] 3.2 Integrate with external-event-ingestion: emit notification on ExternalEventCandidate creation
- [ ] 3.3 Ensure notification service is extensible for future event types

## 4. API Layer

- [ ] 4.1 Create Pydantic schemas for Notification (list response, mark actions)
- [ ] 4.2 Implement `GET /api/v1/notifications` with district_id filter and unread_only option
- [ ] 4.3 Implement `POST /api/v1/notifications/{id}/read`
- [ ] 4.4 Implement `POST /api/v1/notifications/{id}/dismiss`
- [ ] 4.5 Implement `POST /api/v1/notifications/read-all`
- [ ] 4.6 Protect endpoints with RBAC (district scope)

## 5. Frontend

- [ ] 5.1 Add API client methods for notification endpoints
- [ ] 5.2 Add Pinia store for notifications (list, unread count, mark read/dismiss)
- [ ] 5.3 Implement notification badge component in navigation
- [ ] 5.4 Implement notification center (slide-over or modal) with list and actions
- [ ] 5.5 Implement polling (every 60s) or SSE for unread count updates
- [ ] 5.6 Add deep-link navigation from notification to referenced entity

## 6. Tests

- [ ] 6.1 Unit tests for Notification domain model
- [ ] 6.2 Unit tests for notification API endpoints
- [ ] 6.3 Unit tests for notification creation service
- [ ] 6.4 Frontend component tests for badge and notification center
