## ADDED Requirements

### Requirement: Persistent in-app notifications
The system SHALL store notifications persistently until marked as read or dismissed.

#### Scenario: Unread notification visible on login
- **WHEN** a user logs in and unread notifications exist for their district
- **THEN** the system SHALL display unread notifications in the dashboard

#### Scenario: Notification marked as read
- **WHEN** a user marks a notification as read
- **THEN** the system SHALL set `is_read = true`

#### Scenario: Notification dismissed
- **WHEN** a user dismisses a notification
- **THEN** the system SHALL set `is_dismissed = true`
- **THEN** the notification SHALL no longer appear in the default list

### Requirement: Notification entity
The `Notification` SHALL include fields: id, district_id, user_id (nullable), notification_type, title, message, reference_type, reference_id, is_read, is_dismissed, created_at.

#### Scenario: Notification created
- **WHEN** a notification is created
- **THEN** it SHALL have a unique UUID, the current timestamp, and default `is_read=false`, `is_dismissed=false`
