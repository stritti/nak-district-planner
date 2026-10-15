# planning-visibility Specification

## Purpose

One visibility rule for planning slots across the matrix, the event list and the ICS export: which congregation sees which slot, which slots are released to outside audiences, and what public, internal and personal feeds may reveal.

## Requirements

### Requirement: Shared congregation visibility predicate
The system SHALL decide whether a planning slot belongs to a congregation with a single domain predicate, `PlanningSlot.is_visible_to(congregation_id)`, used by the planning matrix, the congregation event view and the ICS export. A congregation slot SHALL be visible only to its own congregation. A district slot SHALL be visible only to congregations listed in its `applicability` or to all congregations when `applicability` contains `"all"`; an empty `applicability` SHALL mean "not distributed".

#### Scenario: District slot distributed to one congregation
- **WHEN** a district slot has `applicability=["<congregation A>"]`
- **THEN** it is visible to congregation A and not to congregation B

#### Scenario: District slot distributed to all congregations
- **WHEN** a district slot has `applicability=["all"]`
- **THEN** it is visible to every congregation of the district

#### Scenario: District slot without applicability
- **WHEN** a district slot has an empty `applicability`
- **THEN** it is visible to no congregation

### Requirement: Approval policy for distribution
The system SHALL distribute district slots to congregations only when they are `ACTIVE` and have `approval_status=CONFIRMED`. A congregation's own slots SHALL remain visible to it in every state.

#### Scenario: Planned district slot stays a draft
- **WHEN** a district slot with `applicability=["all"]` has `approval_status=PLANNED`
- **THEN** it does not appear in any congregation event view

#### Scenario: Imported holidays reach every congregation
- **WHEN** a holiday is imported after a congregation was created
- **THEN** the holiday slot carries `applicability=["all"]` and `CONFIRMED` and appears in that congregation's event view and feed

#### Scenario: Confirmed district slot is distributed
- **WHEN** a district slot with `applicability=["all"]` is `ACTIVE` and `CONFIRMED`
- **THEN** it appears in every congregation event view

### Requirement: Matrix shows only active applicable slots
The planning matrix SHALL consider only `ACTIVE` slots. A cell SHALL show the congregation's own slot before a visible district slot, earliest planning time first.

#### Scenario: Cancelled slot is not a gap
- **WHEN** the only slot of a congregation on a service date is `CANCELLED`
- **THEN** the cell is empty and not marked as LÜCKE

#### Scenario: Cancelled earlier slot does not hide an active slot
- **WHEN** a congregation has a cancelled 09:30 slot and an active 10:00 slot with an assignment on the same date
- **THEN** the cell shows the 10:00 slot and its leader

#### Scenario: District slot only in applicable rows
- **WHEN** a district slot applies to congregation A only
- **THEN** it appears in A's row and not in congregation B's row

### Requirement: ICS export follows the shared visibility rules
The ICS export SHALL include, for congregation tokens, the congregation's own slots plus district slots distributed to it; for personal leader tokens, only slots assigned to that leader. PUBLIC tokens SHALL export only `CONFIRMED` slots regardless of the `approval_status` query parameter; INTERNAL tokens MAY use the parameter and default to including `PLANNED` slots. PUBLIC tokens without a leader SHALL NOT export slots whose event instance has `visibility=INTERNAL`.

#### Scenario: Congregation feed contains distributed district events
- **WHEN** a congregation token's feed is requested and a confirmed district slot applies to that congregation
- **THEN** the feed contains the district slot

#### Scenario: PUBLIC token cannot request drafts
- **WHEN** a PUBLIC token's feed is requested with `?approval_status=include_planned`
- **THEN** `PLANNED` slots are not exported

#### Scenario: PUBLIC feed omits internal events
- **WHEN** a PUBLIC congregation token's feed contains a distributed slot whose event instance is `INTERNAL`
- **THEN** the slot, its title and description are not exported, while INTERNAL and personal leader feeds include it

#### Scenario: Leader feed is personal
- **WHEN** a leader token's feed is requested
- **THEN** only slots with an assignment for that leader are exported

### Requirement: Export tokens read only the leaders they name
Under row-level security the leaders SELECT policy SHALL let an export token read the leader of a personal leader feed and, for INTERNAL tokens, the leaders of the token's district. PUBLIC tokens SHALL read no leader rows; their feeds mark assigned services as `Dienstleiter: [Name anonymisiert]`.

#### Scenario: INTERNAL feed with a leader_id-only assignment
- **WHEN** an INTERNAL export of the district contains a slot whose assignment references only a leader id
- **THEN** the event carries `Dienstleiter: <name>` although the request is unauthenticated

#### Scenario: PUBLIC feed
- **WHEN** a PUBLIC export contains the same slot
- **THEN** the event carries `Dienstleiter: [Name anonymisiert]` and no leader row is read

### Requirement: ICS change semantics
The ICS export SHALL keep UIDs stable (`{slot_id}@nak-bezirksplaner`), SHALL emit `STATUS:CANCELLED` for cancelled slots, and SHALL derive `DTSTAMP` and `LAST-MODIFIED` from the latest `updated_at` of everything rendered into the event (slot, event instance, displayed leader, congregation) and `SEQUENCE` from the seconds since 2020-01-01 of that revision, so it stays within the 32-bit RFC 5545 INTEGER.

#### Scenario: Cancelled slot removed from subscribed calendars
- **WHEN** a slot that was previously exported is cancelled
- **THEN** the feed emits it with the same UID and `STATUS:CANCELLED`

#### Scenario: Updated slot increases SEQUENCE
- **WHEN** a slot's `updated_at` advances
- **THEN** its `LAST-MODIFIED` reflects the new time and its `SEQUENCE` increases

#### Scenario: Leader or congregation rename updates the event revision
- **WHEN** the displayed leader or the slot's congregation is renamed
- **THEN** the exported event's `LAST-MODIFIED` and `SEQUENCE` advance although the slot itself is unchanged

### Requirement: Organisational duty assignees receive personal event visibility
A securely verified registered user linked as an organisational duty assignee SHALL see the corresponding planning slot in their authenticated personal calendar, including slots on which they are not liturgical service leader. Existing visibility, cancellation, confirmed-status and distribution rules SHALL remain applicable to public and congregation views.

#### Scenario: Additional constraints for Organisational duty assignees receive personal event visibility
- **GIVEN** this requirement is applicable
- **WHEN** the system processes the relevant operation
- **THEN** Assignments quarantined after a congregation move SHALL NOT become visible in the destination's ordinary event or personal feeds before authorised revalidation. Name-only participants and unlinked leader records SHALL NOT gain personal calendar eligibility through duty text; the authenticated view SHALL apply the linked subject's current memberships, and each token-based personal view SHALL remain district-scoped. The system SHALL not disclose task assignees through anonymous or public calendar data.

#### Scenario: Person only holds an organisational duty
- **WHEN** an authenticated user with a securely linked subject is assigned as Organist on an eligible active planning slot but is not its service leader
- **THEN** that person can see the slot and their Organist responsibility in their personal calendar

#### Scenario: Duty removed
- **WHEN** the linked user's only assignment to a slot is removed
- **THEN** the slot no longer appears by virtue of that removed duty in their personal calendar

#### Scenario: Name-only participant is not a personal calendar owner
- **WHEN** a planner enters a free-text Organist without a verified account link
- **THEN** no authenticated personal calendar entry or personal token is issued for that name

#### Scenario: Public calendar privacy
- **WHEN** an unauthenticated visitor requests a public feed
- **THEN** the feed exposes neither duty-holder identity nor personal task details
