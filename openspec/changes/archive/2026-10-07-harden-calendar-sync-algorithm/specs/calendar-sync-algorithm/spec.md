## ADDED Requirements

### Requirement: Deterministic sync state machine
The system SHALL manage synchronization using explicit sync states.

#### Scenario: Internal modification
- **WHEN** an internal field is modified
- **THEN** sync_state SHALL transition to DIRTY_INTERNAL

#### Scenario: External modification
- **WHEN** an external update with changed hash is received
- **THEN** sync_state SHALL transition to DIRTY_EXTERNAL

### Requirement: Idempotent external processing
The system SHALL prevent duplicate processing of identical external payloads.

#### Scenario: Duplicate webhook
- **WHEN** an external payload with unchanged hash is received
- **THEN** the system SHALL ignore the update

### Requirement: Loop prevention
The system SHALL prevent infinite update loops between internal and external systems.

#### Scenario: Outbound revision match
- **WHEN** an inbound event contains the same revision marker as last outbound push
- **THEN** the system SHALL ignore the inbound update

### Requirement: Structural conflict detection
The system SHALL detect structural conflicts between internal and external changes.

#### Scenario: Concurrent structural change
- **WHEN** both internal and external structural fields are modified before sync reconciliation
- **THEN** sync_state SHALL transition to CONFLICT

### Requirement: Configurable delete behavior
The system SHALL respect integration-specific delete behavior.

#### Scenario: External deletion with MARK_CANCELLED
- **WHEN** delete_behavior is MARK_CANCELLED
- **THEN** the PlanningSlot SHALL be marked as cancelled instead of removed
