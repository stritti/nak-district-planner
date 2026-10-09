## ADDED Requirements

### Requirement: Typed, scoped autocomplete
The system SHALL remember manually entered organisational duty names as autocomplete suggestions specific to their duty category and authorised district/congregation scope. Matching SHALL be case/whitespace-normalised, avoid duplicates and avoid disclosing suggestions across tenant boundaries. Entering a new valid name SHALL remain possible even if no suggestion matches.

#### Scenario: Reuse previous name
- **WHEN** a planner enters a previously recorded active Organist name in the same effective scope
- **THEN** autocomplete suggests the remembered name for Organist

#### Scenario: Different task type
- **WHEN** the planner edits Dirigent and a person was only recorded for Organist
- **THEN** that name is not suggested from the Organist list

#### Scenario: Foreign district
- **WHEN** a planner searches names from district A
- **THEN** names stored only in district B are not returned

### Requirement: Remove suggestions without deleting assignments
Authorised administrators SHALL be able to suppress a saved suggestion from future autocomplete results, while retaining the underlying record or historical name snapshots and references. A hidden suggestion SHALL NOT be automatically revived by older assignments, imports or reads. Explicit re-entry MAY reactivate it with a deliberate write.

#### Scenario: Former volunteer
- **WHEN** an administrator removes a no-longer-available Organist from autocomplete
- **THEN** that name stops appearing in new Organist suggestions and past event entries remain intact

#### Scenario: Old event viewed
- **WHEN** an older event contains a suppressed name
- **THEN** its historical assignment is still readable and viewing it does not restore the autocomplete suggestion

### Requirement: Authorised suggestion administration
Suggestion searches and modifications SHALL enforce existing tenant isolation, event scope and role permissions. Administration SHALL be auditable, and concurrent duplicate submissions SHALL converge to one active suggestion per effective scope, duty category and normalised name.

#### Scenario: Unauthorised deletion
- **WHEN** a user without administrative rights attempts to suppress another congregation's suggestion
- **THEN** the operation is rejected without modifying the suggestion
