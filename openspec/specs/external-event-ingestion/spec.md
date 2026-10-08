# external-event-ingestion Specification

## Purpose

Governs how external calendar events without an existing link enter the planning model: only exact, safe matches are linked automatically; everything else becomes an `ExternalEventCandidate` reviewed by a district admin. No `PlanningSlot` is created from an external event without review.

## Requirements

### Requirement: Governance-safe exact auto-matching
The system SHALL link an unlinked external event automatically only to an `ACTIVE` `PlanningSlot` of the integration's district and congregation whose UTC date and time equal the event start and whose category is unset or equal to the integration's `default_category`. The event title SHALL NOT be interpreted as a category. The slot SHALL be locked with an advisory lock and SHALL be assignable only if it has no instance or an unlinked `CLEAN` instance.

#### Scenario: Exact compatible match
- **WHEN** an unlinked event matches such a slot
- **THEN** an `EventInstance` and `ExternalEventLink` are created or updated and no candidate is created

#### Scenario: Slot already linked or locally changed
- **WHEN** the matching slot is linked to another integration or has unresolved local changes
- **THEN** a pending candidate is created or kept instead

### Requirement: Review candidates for unmatched events
An unlinked event without a safe match SHALL create one `PENDING` `ExternalEventCandidate` per integration and external event ID, together with a `CANDIDATE_REVIEW` in-app notification. Accepted or dismissed candidates SHALL NOT be reopened by later syncs, and events whose end is not after their start SHALL be skipped. Each candidate SHALL be persisted in a savepoint so one failing event does not abort the run.

#### Scenario: Same event in consecutive syncs
- **WHEN** an unmatched event is fetched again
- **THEN** the existing candidate is refreshed and no duplicate is created

#### Scenario: Source cancelled before review
- **WHEN** a pending candidate's source event is cancelled
- **THEN** the candidate becomes `DISMISSED`

#### Scenario: Pending candidate later matches exactly
- **WHEN** a pending candidate's source event becomes an exact, safely assignable match
- **THEN** the mapping is persisted and the candidate becomes `ACCEPTED` with `matched_slot_id`

### Requirement: Candidate review API
The system SHALL provide `GET /api/v1/external-candidates?district_id=&status=` (default `PENDING`, paginated), `POST /api/v1/external-candidates/{id}/accept` with optional `matched_slot_id`, and `POST /api/v1/external-candidates/{id}/dismiss`, all requiring `DISTRICT_ADMIN` in the candidate's district. Accepting without a slot SHALL create a new `PlanningSlot` from the candidate; a given slot SHALL be active, in the same district and not linked elsewhere.

#### Scenario: Accept into an existing slot
- **WHEN** an admin accepts a candidate with a valid `matched_slot_id`
- **THEN** the candidate becomes `ACCEPTED`, `reviewed_at`/`reviewed_by` are set and the event is linked to that slot

#### Scenario: Candidate already reviewed
- **WHEN** an admin accepts or dismisses a candidate that is no longer pending
- **THEN** the API responds with 409

### Requirement: Candidate review UI
The frontend SHALL provide an external-candidates view for district admins that lists pending candidates and lets them accept (creating a new slot) or dismiss them.

#### Scenario: Admin dismisses a candidate
- **WHEN** a district admin dismisses a candidate in the review view
- **THEN** it disappears from the pending list
