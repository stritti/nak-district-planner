## ADDED Requirements

### Requirement: Reversible deactivation and removal from visible lists
The system SHALL support an active status and a separate reversible hidden-from-lists status for ministers/service leaders, without physically deleting their identities or historical assignment references. Deactivated or hidden people SHALL be absent from default current-person lists and selectors; explicitly authorised administration and historical views SHALL resolve retained entries.

#### Scenario: Minister is deactivated
- **WHEN** a district administrator deactivates a minister
- **THEN** the minister disappears from ordinary selection lists and cannot receive new service assignments, while existing event assignments continue to display the correct name

#### Scenario: Hide an inactive minister
- **WHEN** an authorised administrator hides a deactivated minister from normal frontend listings
- **THEN** the record remains in the database with existing foreign keys intact and the minister is absent from the normal list

#### Scenario: Restore visibility
- **WHEN** an authorised administrator restores the hidden minister's visibility
- **THEN** the administrative list can show the minister again, without implicitly changing the active status

### Requirement: Inclusive end date limits future service eligibility
A minister SHALL support an optional local-calendar `service_end_date`. Assignment eligibility SHALL be checked against the target planning slot's local date across all individual, matrix and bulk assignment entry points. A minister SHALL be eligible on the end date if active and visible, but SHALL NOT be eligible on any later date. The server SHALL apply the same eligibility check to all assignment entry points, including free-text leader names that match a known ineligible leader of the district. Such input MUST NOT silently bypass retirement checks; a distinct guest with the same name requires an explicit guest-only assignment flow that does not claim the retired person's ID. An absent end date SHALL impose no date limit.

#### Scenario: Last day of service
- **WHEN** an active, visible minister has an end date of 2026-12-31 and a slot is dated 2026-12-31
- **THEN** the minister remains eligible for the slot subject to existing conflict checks

#### Scenario: Planning beyond end date
- **WHEN** a planner assigns that minister to a slot dated 2027-01-01
- **THEN** the server rejects the new assignment and the frontend excludes the minister from suggested candidates

#### Scenario: Retired leader entered as free-text
- **WHEN** a planner types the name of a known ineligible leader instead of selecting their record
- **THEN** the server rejects any implicit assignment to that leader and requires an explicit separate guest flow if a different person shares the same name

#### Scenario: Stale client
- **WHEN** the minister's end date is changed after a planner loads the page
- **THEN** a later assignment save is revalidated by the server and rejected if the slot is beyond the new end date

#### Scenario: No end date
- **WHEN** an active, visible minister has no end date
- **THEN** eligibility follows the existing availability and conflict policies without an artificial cutoff

### Requirement: Historical preservation and forward-plan review
Changing active status, visibility or end date SHALL NOT erase historical minister data or silently remove existing service assignments. Assignments already scheduled after a newly entered end date SHALL be flagged for review by authorised planners.

#### Scenario: End date shortened
- **WHEN** a minister's end date is updated to precede an existing planned service
- **THEN** the planned assignment remains recorded but is visibly flagged as ineligible for review and reassignment

#### Scenario: Historical event view
- **WHEN** a minister was hidden or deactivated after serving a past Gottesdienst
- **THEN** authorised historical views still display the minister's identity and assignment

### Requirement: Secure lifecycle management and migration
Minister lifecycle changes SHALL require the appropriate scoped administration permission, enforce tenant isolation and be auditable. An additive migration SHALL initialise existing ministers to active, visible and with no end date, preserving all keys and references.

#### Scenario: Cross-district change
- **WHEN** an administrator in district A tries to deactivate a minister from district B
- **THEN** the request is rejected and the minister remains unchanged

#### Scenario: Migrated minister
- **WHEN** an existing minister record is migrated
- **THEN** it remains eligible under previous rules until an administrator explicitly changes status, visibility or end date
