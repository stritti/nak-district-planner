## ADDED Requirements

### Requirement: ExternalEventCandidate entity
The system SHALL define an `ExternalEventCandidate` entity for review-based ingestion.

#### Scenario: Candidate created for unmatched external event
- **WHEN** an external event is detected with no existing `PlanningSlot` mapping and no exact match
- **THEN** the system SHALL create an `ExternalEventCandidate` with status=PENDING

#### Scenario: Deduplication check
- **WHEN** the same external event is detected in consecutive syncs
- **THEN** the system SHALL NOT create a duplicate candidate (check by external_event_id + source)

### Requirement: ExternalEventCandidate fields
The `ExternalEventCandidate` SHALL include fields: id, district_id, external_event_id, source, congregation_id, event_date, event_time, title, category, status, matched_slot_id, created_at, reviewed_at, reviewed_by.

#### Scenario: Candidate created with all available data
- **WHEN** an `ExternalEventCandidate` is created
- **THEN** it SHALL populate all known fields from the external event data
