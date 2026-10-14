## Why

Governance-relevant events (new external events detected, sync errors, LÜCKE) currently have no notification channel. Administrators must actively poll the system to discover these situations. A persistent in-app notification system is needed to surface these events in the UI.

## What Changes

- Introduce persistent `Notification` entity with read/dismiss semantics
- Create notifications when an `ExternalEventCandidate` is created
- API endpoints for listing, marking as read, and dismissing notifications
- Frontend notification badge and notification center view

## Capabilities

### New Capabilities
- `notification-persistence`: Store notifications persistently until marked as read or dismissed
- `notification-emission`: Create notifications when governance-relevant events occur (e.g., ExternalEventCandidate created)
- `notification-api`: REST endpoints for listing, marking as read, and dismissing notifications
- `notification-ui`: Frontend badge indicator and notification center

### Modified Capabilities
- *(none – purely additive)*

## Impact

- **Domain Model** — New `Notification` entity (type, message, is_read, created_at)
- **Database** — New migration for `notifications` table
- **API** — New endpoints: `GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/{id}/dismiss`
- **Frontend** — Notification badge in nav, notification center view
