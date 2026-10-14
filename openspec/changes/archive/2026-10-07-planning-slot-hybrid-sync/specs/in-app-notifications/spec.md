## ADDED Requirements

### Requirement: Persistent in-app notifications
The system SHALL store notifications persistently until marked as read or dismissed.

#### Scenario: Unread notification visible on login
- **WHEN** a user logs in and unread notifications exist
- **THEN** the system SHALL display them in the dashboard

### Requirement: Notification on external event detection
The system SHALL create a notification when an ExternalEventCandidate is created.

#### Scenario: Candidate created
- **WHEN** an ExternalEventCandidate is created
- **THEN** a Notification of type EXTERNAL_EVENT_DETECTED SHALL be stored
