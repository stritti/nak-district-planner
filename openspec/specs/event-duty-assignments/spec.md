# event-duty-assignments Specification

## Purpose
Define optional, scoped organisational duty assignments on planning slots, including identity, capacity, history and personal-calendar behavior.

## Requirements

### Requirement: Optional organisational duties on planning slots
A `PlanningSlot` SHALL support zero or more organisational duty assignments independently of its existing single liturgical service-leader assignment. Each assignment SHALL reference a configured category and exactly one of: a securely resolved registered-user subject (`linked_user_sub`) within the authorised district/event context, or a validated scoped name-only participant and immutable display-name snapshot.

#### Scenario: Additional constraints for Optional organisational duties on planning slots
- **GIVEN** this requirement is applicable
- **WHEN** the system processes the relevant operation
- **THEN** A linked leader/person record is eligible for personal feeds only if its `user_sub` is securely verified. A plain-text name or unlinked leader record SHALL NOT be treated as a user account. A slot SHALL remain valid, confirmable and publishable with no organisational assignments.

#### Scenario: Unassigned service
- **WHEN** a Gottesdienst planning slot is created with no persons selected for Schließdienst, Organist or Dirigent
- **THEN** the slot can be saved and confirmed without additional validation errors

#### Scenario: Existing leader assignment
- **WHEN** a slot already has one liturgical service leader
- **THEN** assigning multiple organisational duty types does not violate the unique service-leader constraint

### Requirement: Validate category, person and capacity
The system SHALL reject unknown or cross-tenant category/person identifiers, assignments to categories not enabled for the slot's effective event category, duplicate linked-subject/duty pairs or duplicate normalised name-only/duty pairs within a slot, and assignments exceeding configured duty capacity. Checks and writes SHALL be concurrency safe, with no partial writes on failure.

#### Scenario: Additional constraints for Validate category, person and capacity
- **GIVEN** this requirement is applicable
- **WHEN** the system processes the relevant operation
- **THEN** These two identity types SHALL use separate database-backed uniqueness constraints that correctly handle nullable fields; capacity checks SHALL be serialised per slot/duty. Changing the planning slot's category or effective congregation SHALL NOT silently delete existing duty assignments; newly incompatible assignments SHALL be visibly flagged for review and SHALL NOT be newly added or reassigned until valid for the new category and scope. An assignment SHALL retain its original owning scope. Moving a slot to another congregation SHALL quarantine old-scope assignments until explicit revalidation by an administrator/planner authorised in both scopes, and SHALL prevent private names or duties from being exposed in the new congregation's normal views or personal feeds before revalidation.

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

#### Scenario: Slot moves to another congregation
- **WHEN** an event with a name-only Organist from congregation A moves to congregation B
- **THEN** the assignment remains in the audit/history record but is flagged for review
- **AND** congregation B's ordinary views and personal feeds do not expose the original private name without authorised revalidation

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

### Requirement: One person cannot hold overlapping duties
Creating or replacing a duty assignment SHALL be rejected when the same person holds a duty at an overlapping event of the district: a match through the same linked account blocks, a match only through the same normalised typed name warns and may be acknowledged with `confirm_warnings`. Responses SHALL use the conflict contract of service assignments (HTTP 409 with `conflicts`).

#### Scenario: Duties of other congregations
- **WHEN** a congregation-scoped planner assigns a person who holds an overlapping duty in another congregation they cannot read
- **THEN** the conflict is still detected, through a lookup that returns only the event, congregation, time window and match strength, and only to planners of the district

#### Scenario: Overlap definition
- **WHEN** two duties of one person are compared
- **THEN** their events overlap if the instance times (or the planned time plus the configured default duration) overlap
- **AND** a duty of the same event does not count and the check is skipped when conflict checks are disabled

#### Scenario: Same account, overlapping event
- **WHEN** a duty is assigned to an account that holds a duty at an overlapping event, in this or another congregation
- **THEN** the API responds with 409 and a `BLOCK` conflict `duty_double_booking`, and nothing is saved

#### Scenario: Same name only
- **WHEN** a duty is assigned by typed name and another duty with the same normalised name overlaps
- **THEN** the API responds with 409 and a `WARN` conflict `duty_possible_namesake`
- **AND** the request succeeds when repeated with `confirm_warnings`

#### Scenario: Back-to-back events
- **WHEN** the other duty ends exactly when this event starts
- **THEN** there is no conflict

#### Scenario: Cancelled events and other districts
- **WHEN** the other duty belongs to a cancelled event or to another district
- **THEN** it is ignored

### Requirement: A duty may reference an existing leader
A duty assignment SHALL have exactly one identity: a typed name, a verified account or an existing leader of the district. A referenced leader SHALL be eligible on the event date; the assignment stores a display snapshot of the leader's rank and name. Duties of the same leader, of the leader's own account and the leader's service assignments at overlapping events SHALL block the write, and a plain typed name SHALL match only duties without a leader reference.

#### Scenario: Leader as organist
- **WHEN** a planner assigns an eligible leader of the district to a duty
- **THEN** the duty stores the leader reference and the display snapshot, and no name suggestion is remembered

#### Scenario: One person under two identities
- **WHEN** a leader and the account linked to that leader are added to the same duty of one event
- **THEN** the second addition is rejected as a duplicate identity

#### Scenario: Unusable leader
- **WHEN** the leader is unknown, belongs to another district, is inactive, hidden or retired before the event
- **THEN** the API answers as for any unknown reference (404) and saves nothing

#### Scenario: Duty and service at the same time
- **WHEN** the leader leads a service at an overlapping event, in this or another congregation
- **THEN** the duty is blocked with a `duty_double_booking` conflict
- **AND** a duty naming an account is checked against the duties and services of every leader linked to that account in the same way

#### Scenario: Leader assigned to a service
- **WHEN** a leader is assigned to a service while holding an overlapping duty, or the leader's own account does
- **THEN** the assignment conflict check reports the overlap like another service, with the same severities

#### Scenario: Choosing a leader in the panel
- **WHEN** a planner edits the duties of an event
- **THEN** the panel offers the leaders the planner may read (leader RLS) and that are eligible on the event date as a third identity next to free name and account, and shows such a duty as "Amtsträger"
- **AND** the choice list is authorized like the duty write, so congregation-scoped planners receive it as well (their own congregation's leaders), with only id, name and rank

#### Scenario: Concurrent duty and service of one leader
- **WHEN** a duty and a service assignment of the same leader for overlapping times are written concurrently
- **THEN** both writes take the same per-leader and per-account transaction locks (also when the duty names the leader's linked account), so at most one of them passes its conflict check
- **AND** moving an event re-checks its service leaders under the same per-leader locks followed by the per-account locks of their linked accounts

#### Scenario: Moved and long-running events
- **WHEN** an event has an instance whose actual interval overlaps the new duty
- **THEN** it conflicts whatever its planning date, and only events without an instance are judged by their planning date

#### Scenario: Typed names are weak matches for every identity kind
- **WHEN** a typed name equals, after normalisation, the typed name, the account display name or the leader name of another duty
- **THEN** the result is a warning and never a block, whichever duty was entered first

#### Scenario: Several identities
- **WHEN** a request names more than one of name, account and leader, or a name suggestion together with a leader
- **THEN** the request is rejected by validation
