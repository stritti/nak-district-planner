## ADDED Requirements

### Requirement: List notifications endpoint
The system SHALL provide `GET /api/v1/notifications` with district filtering.

#### Scenario: List notifications
- **WHEN** a user calls `GET /api/v1/notifications?district_id={id}`
- **THEN** the system SHALL return notifications for that district, newest first
- **THEN** the response SHALL include a `total_unread` count

#### Scenario: Filter unread only
- **WHEN** a user calls `GET /api/v1/notifications?district_id={id}&unread_only=true`
- **THEN** the system SHALL return only notifications where `is_read=false` and `is_dismissed=false`

### Requirement: Mark as read endpoint
The system SHALL provide `POST /api/v1/notifications/{id}/read`.

#### Scenario: Mark notification as read
- **WHEN** a user calls `POST /api/v1/notifications/{id}/read`
- **THEN** the system SHALL set `is_read = true`

### Requirement: Dismiss notification endpoint
The system SHALL provide `POST /api/v1/notifications/{id}/dismiss`.

#### Scenario: Dismiss notification
- **WHEN** a user calls `POST /api/v1/notifications/{id}/dismiss`
- **THEN** the system SHALL set `is_dismissed = true`

### Requirement: Mark all as read endpoint
The system SHALL provide `POST /api/v1/notifications/read-all`.

#### Scenario: Mark all as read
- **WHEN** a user calls `POST /api/v1/notifications/read-all`
- **THEN** the system SHALL set `is_read = true` for all unread, non-dismissed notifications for that district
