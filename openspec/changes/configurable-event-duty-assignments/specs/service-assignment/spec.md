## ADDED Requirements

### Requirement: Minister retirement and visibility lifecycle
Ministers/service leaders SHALL support independent active and frontend-list visibility states and an optional inclusive service end date. Deactivation and hide-from-list operations SHALL retain database rows, IDs and historical references. Default person selection and visible management lists SHALL exclude hidden or deactivated ministers, while authorised historical/administrative views MAY explicitly include them. Restoring visibility and reactivation SHALL require authorised, audited operations.

#### Scenario: Deactivate minister
- **WHEN** an administrator deactivates a minister
- **THEN** that minister is excluded from normal new-assignment choices but existing and historical service assignments retain the same referenced identity

#### Scenario: Hide deactivated minister
- **WHEN** an administrator removes a deactivated minister from visible lists
- **THEN** no database hard delete occurs, historical references remain valid, and the minister can be retrieved with an authorised include-inactive query

### Requirement: Minister service end date affects planning
A minister with an end-of-service date SHALL be eligible for new service assignments only through that local calendar date, inclusive, and only when active and not hidden. Server-side validation SHALL enforce the date and status for event-list, matrix and bulk assignment paths. Earlier assignments SHALL not be silently deleted when the end date changes; future ineligible ones SHALL be flagged for review.

#### Scenario: Before or on end date
- **WHEN** an active visible minister with an end date of 2026-12-31 is assigned a service on 2026-12-31
- **THEN** date-based eligibility permits the assignment subject to all other conflict rules

#### Scenario: Beyond end date
- **WHEN** a planner attempts to assign that minister to a service dated 2027-01-01
- **THEN** the server rejects the assignment and the planning UI identifies the unavailability

#### Scenario: End date moved earlier
- **WHEN** a minister's end date is changed to precede already planned services
- **THEN** those assignments remain historically referentially intact and are flagged as requiring planner review

#### Scenario: Stale client tries inactive minister
- **WHEN** a stale client submits a new service assignment for an inactive or hidden minister
- **THEN** the server rejects it regardless of whether the frontend still shows that person
