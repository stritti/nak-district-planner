## ADDED Requirements

### Requirement: Notification on external event detection
The system SHALL create a notification when an `ExternalEventCandidate` is created.

#### Scenario: Candidate created triggers notification
- **WHEN** an `ExternalEventCandidate` is created
- **THEN** a `Notification` of type `EXTERNAL_EVENT_DETECTED` SHALL be stored for the district
- **THEN** the notification SHALL include the candidate title and date in the message

#### Scenario: Notification references source
- **WHEN** a notification is created for an `ExternalEventCandidate`
- **THEN** the notification SHALL set `reference_type = "external_event_candidate"` and `reference_id` to the candidate's UUID
