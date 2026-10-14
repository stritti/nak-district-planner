## ADDED Requirements

### Requirement: Notification badge in navigation
The system SHALL display an unread notification count badge in the top navigation bar.

#### Scenario: Badge shows unread count
- **WHEN** a user is logged in and has unread notifications
- **THEN** the navigation SHALL display a badge with the unread count

#### Scenario: No badge for zero unread
- **WHEN** a user has no unread notifications
- **THEN** the badge SHALL NOT be displayed (or show zero subtly)

### Requirement: Notification center view
The system SHALL provide a notification center view accessible from the badge.

#### Scenario: Open notification center
- **WHEN** a user clicks the notification badge
- **THEN** a notification center SHALL open (slide-over or modal)
- **THEN** it SHALL display the list of unread notifications with title, message, and time

#### Scenario: Notification with reference link
- **WHEN** a notification has a `reference_id`
- **THEN** the notification SHALL have a clickable "Ansehen" (View) button that navigates to the referenced entity

#### Scenario: Mark all as read from UI
- **WHEN** a user clicks "Alle gelesen" in the notification center
- **THEN** the system SHALL mark all notifications as read and update the badge count
