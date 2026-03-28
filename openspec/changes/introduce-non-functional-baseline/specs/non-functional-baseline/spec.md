## ADDED Requirements

### Requirement: Performance baseline
The system SHALL meet defined latency and execution thresholds under normal district-scale load.

#### Scenario: Matrix latency
- **WHEN** a matrix view is requested for a district with up to 50 congregations and a 3-month range
- **THEN** the API response time SHALL be ≤ 500ms under normal load

### Requirement: Credential encryption
The system SHALL encrypt all external calendar credentials at rest.

#### Scenario: Store credentials
- **WHEN** credentials are stored in the database
- **THEN** they SHALL be encrypted using application-level encryption

### Requirement: Secure export tokens
The system SHALL generate export tokens with at least 128-bit entropy.

#### Scenario: Generate token
- **WHEN** a new export token is created
- **THEN** the token SHALL be cryptographically secure and unpredictable

### Requirement: Audit logging
The system SHALL record audit entries for governance-relevant actions.

#### Scenario: PlanningSlot modification
- **WHEN** a PlanningSlot is modified
- **THEN** an audit log entry SHALL be created including user, timestamp, and action type

### Requirement: Sync retry policy
The system SHALL apply retry with exponential backoff for transient sync errors.

#### Scenario: Transient sync failure
- **WHEN** a sync attempt fails due to a transient network error
- **THEN** the system SHALL retry using exponential backoff strategy
