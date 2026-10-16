# notifications Specification

## Purpose

Persistent in-app notifications per district (for example external events awaiting review or sync failures) with a navigation badge and a notification center.

## Requirements

### Requirement: Notification persistence
A `Notification` SHALL store district, optional congregation, `type` (`EXTERNAL_EVENT_DETECTED`, `SYNC_CONFLICT`, `CANDIDATE_REVIEW`, `ASSIGNMENT_REMINDER`, `SYSTEM`), title, body, JSON payload, `created_at`, `read_at` and `dismissed_at`. Notifications SHALL remain until read or dismissed.

#### Scenario: Candidate created
- **WHEN** a sync creates an external event candidate
- **THEN** a `CANDIDATE_REVIEW` notification with the candidate ID in its payload is stored for the district

### Requirement: Notification API
The system SHALL provide `GET /api/v1/notifications/{district_id}`, `GET /api/v1/notifications/{district_id}/unread-count`, `POST /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/{id}/dismiss` and `POST /api/v1/notifications/{district_id}/read-all`, each requiring `VIEWER` in the notification's district. Dismissed notifications SHALL NOT appear in the default list.

#### Scenario: Dismiss
- **WHEN** a user dismisses a notification
- **THEN** `dismissed_at` is set and it no longer appears in the list

#### Scenario: Foreign district
- **WHEN** a user marks a notification of a district without membership as read
- **THEN** the API responds with 403

### Requirement: Notification UI
The navigation SHALL show a bell with the unread count; its panel SHALL list notifications with title, body and time and offer read, dismiss, mark-all-read and an "Ansehen" action that deep-links to the referenced entity when a destination is known.

#### Scenario: Open referenced candidate
- **WHEN** a user clicks "Ansehen" on a candidate notification
- **THEN** the app navigates to the external-candidates review view


### Requirement: Notification acknowledgement is user-owned
Notifications SHALL be shared district-scoped records, but `read_at` and `dismissed_at` SHALL be persisted per verified OIDC `sub` in a separate state table. Listing, unread counts, read, dismiss and read-all SHALL operate solely on the requesting user's state, subject to district membership. State rows SHALL be protected by PostgreSQL RLS enforcing both subject ownership and parent-notification visibility. Concurrent updates SHALL preserve the first recorded acknowledgement time.

#### Scenario: One user dismisses another user's unread notification
- **WHEN** viewer A dismisses a district notification
- **THEN** viewer A no longer sees it
- **AND** viewer B in the same district still sees it unread

#### Scenario: User-specific read-all
- **WHEN** viewer A marks all notifications in one district as read
- **THEN** only viewer A's unread counters change
- **AND** viewers in other districts or with different subjects retain their own state

#### Scenario: Migration from legacy shared timestamps
- **WHEN** a database contains notifications with legacy global read/dismiss timestamps
- **THEN** those timestamps keep their pre-migration effect for every user, so previously dismissed notifications stay hidden and previously read ones stay read
- **AND** the legacy timestamps are never written again; new acknowledgements are stored only in the per-subject state table
