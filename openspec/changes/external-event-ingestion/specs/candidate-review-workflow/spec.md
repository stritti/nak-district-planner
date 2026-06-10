## ADDED Requirements

### Requirement: Candidate listing
The system SHALL provide an endpoint to list `ExternalEventCandidate` records.

#### Scenario: List pending candidates
- **WHEN** an administrator requests `GET /api/v1/external-candidates?district_id={id}&status=PENDING`
- **THEN** the system SHALL return all pending candidates for that district, newest first

### Requirement: Accept candidate and map to existing slot
The system SHALL allow administrators to accept a candidate and link it to an existing `PlanningSlot`.

#### Scenario: Accept and map
- **WHEN** an administrator accepts a candidate with a selected existing `PlanningSlot`
- **THEN** the system SHALL set status=ACCEPTED, store the mapping, and update `matched_slot_id`

### Requirement: Accept candidate and create new slot
The system SHALL allow administrators to accept a candidate and create a new `PlanningSlot`.

#### Scenario: Accept and create
- **WHEN** an administrator accepts a candidate without selecting an existing slot
- **THEN** the system SHALL create a new `PlanningSlot` from the candidate's data
- **THEN** the system SHALL set status=ACCEPTED and link the candidate to the new slot

### Requirement: Dismiss candidate
The system SHALL allow administrators to dismiss a candidate.

#### Scenario: Dismiss
- **WHEN** an administrator dismisses a candidate
- **THEN** the system SHALL set status=DISMISSED and `reviewed_at` to the current time
