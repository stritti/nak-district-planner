## ADDED Requirements

### Requirement: Optional organisational duties on planning slots
A `PlanningSlot` SHALL support zero or more organisational duty assignments independently of its existing single liturgical service-leader assignment. Each assignment SHALL reference a configured category and exactly one of: a securely resolved registered-user subject (`linked_user_sub`) within the authorised district/event context, or a validated scoped name-only participant and immutable display-name snapshot. A linked leader/person record is eligible for personal feeds only if its `user_sub` is securely verified. A plain-text name or unlinked leader record SHALL NOT be treated as a user account. A slot SHALL remain valid, confirmable and publishable with no organisational assignments.

#### Scenario: Unassigned service
- **WHEN** a Gottesdienst planning slot is created with no persons selected for Schließdienst, Organist or Dirigent
- **THEN** the slot can be saved and confirmed without additional validation errors

#### Scenario: Existing leader assignment
- **WHEN** a slot already has one liturgical service leader
- **THEN** assigning multiple organisational duty types does not violate the unique service-leader constraint

### Requirement: Validate category, person and capacity
The system SHALL reject unknown or cross-tenant category/person identifiers, assignments to categories not enabled for the slot's effective event category, duplicate linked-subject/duty pairs or duplicate normalised name-only/duty pairs within a slot, and assignments exceeding configured duty capacity. These two identity types SHALL use separate database-backed uniqueness constraints that correctly handle nullable fields; capacity checks SHALL be serialised per slot/duty. Checks and writes SHALL be concurrency safe, with no partial writes on failure. Changing the planning slot's category or effective congregation SHALL NOT silently delete existing duty assignments; newly incompatible assignments SHALL be visibly flagged for review and SHALL NOT be newly added or reassigned until valid for the new category and scope.

#### Scenario: Repeated name-only participant
- **WHEN** a planner adds two name-only assignments to the same duty on the same slot with case/whitespace-equivalent names
- **THEN** at most one logical name-only assignment is stored and the second write returns a validation or conflict result

#### Scenario: Concurrent final-place assignment
- **WHEN** two requests concurrently fill the last available position in a duty category
- **THEN** at most the configured capacity is persisted and the losing request receives a conflict response

#### Scenario: Foreign person
- **WHEN** a planner tries to assign a person outside the authorised district/event scope
- **THEN** the system rejects the operation without exposing foreign-person details

#### Scenario: Multiple tasks for one person
- **WHEN** the same person is assigned Organist and Schließdienst on the same slot
- **THEN** two task assignments are persisted and can be projected as one calendar event with both task labels

#### Scenario: Category changes after an existing assignment
- **WHEN** a planner changes a slot from Gottesdienst to a category where Organist is not enabled
- **THEN** the previous Organist assignment and historical display remain stored and are flagged for review
- **AND** the server rejects a new Organist assignment for that slot until that duty is explicitly enabled

#### Scenario: Unverified user-submitted identity
- **WHEN** a planner submits an arbitrary `linked_user_sub` or both name-only and linked identities
- **THEN** the server rejects the assignment without creating an account, personal feed or token

### Requirement: Scoped assignment management
Only planners with edit permissions for the relevant planning slot SHALL create, replace or remove organisational duty assignments. The system SHALL enforce membership and district isolation for event and person lookups.

#### Scenario: Viewer attempts reassignment
- **WHEN** a user with only `VIEWER` permissions modifies a duty assignment
- **THEN** the request is rejected and the assignment remains unchanged

### Requirement: Assignment lifecycle independent of external sync
Assignments SHALL be bound to `PlanningSlot`; EventInstance creation, replacement or incoming synchronisation SHALL not duplicate or silently erase them.

#### Scenario: External event time changes
- **WHEN** an external update changes the linked EventInstance time
- **THEN** the existing organisational duty assignment remains on the slot and displays using the resolved event time

### Requirement: Names can be entered without a linked account
Organisational duty assignments SHALL support an authorised linked person or a validated name-only entry. Accepting a new name SHALL remember a suggestion scoped to the event's district/congregation and selected duty category. The system SHALL NOT fabricate user identities or personal calendar access for name-only entries; all historical assignments SHALL retain their display name if a suggestion is suppressed.

#### Scenario: Name-only organist
- **WHEN** a planner enters "Anna Beispiel" as Organist for an event without choosing a user account
- **THEN** the name is saved on the event and available as an Organist suggestion for subsequent events in the authorised scope

#### Scenario: Category-specific completion
- **WHEN** a name was previously used only as Organist
- **THEN** entering a Schließdienst name does not suggest that person solely because of the Organist history

#### Scenario: No implicit personal feed
- **WHEN** an assignment is made to a name-only participant without a verified linked user
- **THEN** no authenticated or token-based personal calendar is created or exposed for that name
