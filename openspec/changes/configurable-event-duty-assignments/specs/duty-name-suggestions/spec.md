## ADDED Requirements

### Requirement: Remember duty-specific names from free-text entry
The system SHALL accept validated free-text display names as organisational duty assignees without requiring an application account. After an assignment is saved, the system SHALL remember the normalised name and display name for autocomplete only within the slot's owning scope and the specific duty category: congregation slots use that congregation's suggestion store; district-level slots use the district store. Inherited district duty definitions SHALL NOT implicitly expose district or other congregation names in a congregation's autocomplete. Suggestions SHALL be deduplicated by normalised name within that scope and category.

#### Scenario: Save name for Organist
- **WHEN** a planner saves "Anna Beispiel" as Organist in congregation A
- **THEN** subsequent Organist editors in congregation A offer Anna Beispiel as an autocomplete suggestion

#### Scenario: No cross-duty suggestions
- **WHEN** Anna Beispiel was remembered only as Organist
- **THEN** the Schließdienst editor SHALL NOT offer Anna Beispiel merely from the Organist entry

#### Scenario: Idempotent normalisation
- **WHEN** planners enter " Anna  Beispiel " and "anna beispiel" for the same scope and duty
- **THEN** the suggestion store contains a single normalised candidate without a duplicate

### Requirement: Explicitly suppress and restore autocomplete suggestions
An authorised `PLANNER` in the effective event/duty scope (or a higher scoped role) SHALL be able to suppress or restore a suggestion from the autocomplete list through a dedicated management action, independently of historical event assignments. Removal SHALL be a reversible suppression, not deletion of referenced records. Previously suppressed suggestions SHALL NOT become visible merely through reading, importing or re-saving historical assignments. A deliberate manual re-add or authorised restoration MAY reactivate the suggestion.

#### Scenario: Person moved away
- **WHEN** an authorised planner removes Anna Beispiel from Organist suggestions
- **THEN** the name stops appearing in new Organist autocomplete results but existing event assignments still show Anna Beispiel

#### Scenario: Historical reference does not resurrect
- **WHEN** a suppressed suggestion is used by an existing event read or calendar export
- **THEN** it remains suppressed in autocomplete

#### Scenario: Explicit re-add
- **WHEN** an authorised planner deliberately enters the previously suppressed name as a new Organist candidate
- **THEN** the system can restore the suggestion without creating an unrelated duplicate record

### Requirement: Scoped suggestion access and privacy
The system SHALL restrict suggestion listing and management to the user's authorised planning scope and SHALL not expose another tenant's suggestions. Name-only entries SHALL NOT implicitly create authenticated identities, personal calendar feeds or tokens.

#### Scenario: Viewer cannot manage suggestions
- **WHEN** a user with only `VIEWER` permission tries to hide a suggestion
- **THEN** the request is rejected and the suggestion remains unchanged

#### Scenario: Cross-tenant lookup
- **WHEN** a planner in district A queries a duty suggestion known only to district B
- **THEN** no information from district B is returned

#### Scenario: Unlinked participant
- **WHEN** a name-only assignee has no verified linked user account
- **THEN** the duty is visible in the authorised event display but no personal calendar is provisioned

### Requirement: Concurrent suggestion safety
The system SHALL prevent duplicate suggestions when the same name is saved concurrently in a duty and scope.

#### Scenario: Concurrent first usage
- **WHEN** two planners save the same previously unknown Organist name simultaneously
- **THEN** one logical suggestion remains and both valid event assignments retain their names
