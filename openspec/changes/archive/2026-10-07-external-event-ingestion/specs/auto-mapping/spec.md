## ADDED Requirements

### Requirement: Governance-safe exact auto-matching
The system SHALL automatically map an external event to an existing active `PlanningSlot` only if its congregation, UTC date, and UTC time match exactly and its category is compatible with the integration's configured default category. The external event title SHALL NOT be interpreted as a category.

An integration with no default category SHALL NOT be blocked solely by the slot's category. Where a default category is configured, the slot's category SHALL either be that category or be unset.

#### Scenario: Exact compatible match skips candidate creation
- **WHEN** an external event matches an existing active `PlanningSlot` on congregation_id, UTC planning_date and planning_time, and has a compatible category
- **AND** the slot is not externally linked to another integration and has no unresolved local changes
- **THEN** the system SHALL create an `EventInstance` and `ExternalEventLink` mapping without creating a new `ExternalEventCandidate`

#### Scenario: No default category
- **WHEN** an integration has no default category and the event exactly matches a safely assignable slot
- **THEN** the system SHALL NOT use the event title as a category or reject that match solely due to category

#### Scenario: Partial or unsafe match creates candidate
- **WHEN** an external event does not match on congregation, UTC date or UTC time, or its category is incompatible
- **OR** a matching slot is already externally linked to another integration or has unresolved local changes
- **THEN** the system SHALL create or refresh a pending `ExternalEventCandidate` for manual review
- **AND** the system SHALL continue processing later external events in that sync run

#### Scenario: Previously pending candidate becomes assignable
- **WHEN** an existing pending candidate's source event becomes an exact, safely assignable match
- **THEN** the system SHALL persist the event mapping and mark that candidate ACCEPTED with the matched slot ID
