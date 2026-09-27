## 1. Domain Model

- [x] 1.1 Implement `Notification` entity with fields: id, district_id, user_id (nullable), notification_type, title, message, reference_type, reference_id, is_read, is_dismissed, created_at *(existiert in `app/domain/models/notification.py` — abweichendes Feldschema: `congregation_id` + `payload` JSONB statt `user_id`/`reference_*`/`is_dismissed`; `is_read` als Property auf `read_at`)*

## 2. Persistence Layer

- [x] 2.1 Create Alembic migration for `notifications` table *(`0124_create_notifications_table.py`)*
- [x] 2.2 Implement SQLAlchemy ORM model for `NotificationORM` *(`adapters/db/orm_models/notification.py`)*
- [ ] 2.3 Implement repository with list (filterable, ordered), create, mark-read, mark-dismissed methods *(list/create/mark-read vorhanden in `adapters/db/repositories/notification.py`; mark-dismissed fehlt — siehe 4.4)

## 3. Notification Emission

- [x] 3.1 Implement notification creation service *(app/application/notification_service.py)*
- [ ] 3.2 Integrate with external-event-ingestion: emit notification on ExternalEventCandidate creation *(blockiert bis `external-event-ingestion` umgesetzt ist)*
- [x] 3.3 Ensure notification service is extensible for future event types *(NotificationType-Enum: EXTERNAL_EVENT_DETECTED, SYNC_CONFLICT, CANDIDATE_REVIEW, ASSIGNMENT_REMINDER, SYSTEM)*

## 4. API Layer

- [x] 4.1 Create Pydantic schemas for Notification (list response, mark actions)
- [x] 4.2 Implement `GET /api/v1/notifications` with district_id filter and unread_only option *(Router `notifications.py`: `GET /{district_id}` mit `unread_only`, `limit`, `offset`)*
- [x] 4.3 Implement `POST /api/v1/notifications/{id}/read` *(Status 204)*
- [ ] 4.4 Implement `POST /api/v1/notifications/{id}/dismiss`
- [x] 4.5 Implement `POST /api/v1/notifications/read-all` *(als `POST /{district_id}/read-all`)*
- [x] 4.6 Protect endpoints with RBAC (district scope) *(require_role_in_district mit Role.VIEWER)*

## 5. Frontend

- [x] 5.1 Add API client methods for notification endpoints *(`src/api/notifications.ts`)*
- [x] 5.2 Add Pinia store for notifications (list, unread count, mark read/dismiss) *(`src/stores/notifications.ts`; dismiss fehlt analog 4.4)*
- [x] 5.3 Implement notification badge component in navigation *(`NotificationBell.vue` in `AppNav.vue`)*
- [x] 5.4 Implement notification center (slide-over or modal) with list and actions *(in `NotificationBell.vue` integriert)*
- [x] 5.5 Implement polling (every 60s) or SSE for unread count updates *(60s-Polling im Store)*
- [ ] 5.6 Add deep-link navigation from notification to referenced entity *(fehlt)*

## 6. Tests

- [x] 6.1 Unit tests for Notification domain model *(`tests/unit/test_notification.py`)*
- [x] 6.2 Unit tests for notification API endpoints *(`tests/unit/test_notifications_router.py`)*
- [x] 6.3 Unit tests for notification creation service *(in `test_notification.py` abgedeckt)*
- [ ] 6.4 Frontend component tests for badge and notification center *(fehlt)*
