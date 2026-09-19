## ADDED Requirements

### Requirement: ExternalEventCandidate entity
The system SHALL define an `ExternalEventCandidate` entity for review-based
ingestion from Google Calendar, Microsoft 365/Outlook, ICS, and CalDAV in Phase 2.

#### Scenario: Candidate created for unmatched external event
- **WHEN** an external event from any supported connector is detected with no existing `PlanningSlot` mapping and no exact match
- **THEN** the system SHALL create an `ExternalEventCandidate` with status=PENDING
- **AND** the system SHALL NOT create a new `PlanningSlot` before review

#### Scenario: Deduplication check
- **WHEN** the same external event is detected in consecutive syncs
- **THEN** the system SHALL NOT create a duplicate candidate (check by external_event_id + source)

#### Scenario: Pending candidate source change
- **WHEN** a pending candidate's external event changes before review
- **THEN** the system SHALL update the candidate's event data and content_hash
- **AND** the system SHALL retain the existing candidate rather than create a duplicate

### Requirement: ExternalEventCandidate fields
The `ExternalEventCandidate` SHALL include fields: id, district_id, external_event_id, source, congregation_id, event_date, event_time, title, category, content_hash, status, matched_slot_id, created_at, updated_at, reviewed_at, reviewed_by.

#### Scenario: Candidate created with all available data
- **WHEN** an `ExternalEventCandidate` is created
- **THEN** it SHALL populate all known fields from the external event data
