## ADDED Requirements

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
The ICS export SHALL include, for congregation tokens, the congregation's own slots plus district slots distributed to it; for personal leader tokens, only slots assigned to that leader. PUBLIC tokens SHALL export only `CONFIRMED` slots regardless of the `approval_status` query parameter; INTERNAL tokens MAY use the parameter and default to including `PLANNED` slots.

#### Scenario: Congregation feed contains distributed district events
- **WHEN** a congregation token's feed is requested and a confirmed district slot applies to that congregation
- **THEN** the feed contains the district slot

#### Scenario: PUBLIC token cannot request drafts
- **WHEN** a PUBLIC token's feed is requested with `?approval_status=include_planned`
- **THEN** `PLANNED` slots are not exported

#### Scenario: Leader feed is personal
- **WHEN** a leader token's feed is requested
- **THEN** only slots with an assignment for that leader are exported

### Requirement: ICS change semantics
The ICS export SHALL keep UIDs stable (`{slot_id}@nak-bezirksplaner`), SHALL emit `STATUS:CANCELLED` for cancelled slots, and SHALL derive `DTSTAMP` and `LAST-MODIFIED` from the last revision (`updated_at`) and `SEQUENCE` from its epoch seconds.

#### Scenario: Cancelled slot removed from subscribed calendars
- **WHEN** a slot that was previously exported is cancelled
- **THEN** the feed emits it with the same UID and `STATUS:CANCELLED`

#### Scenario: Updated slot increases SEQUENCE
- **WHEN** a slot's `updated_at` advances
- **THEN** its `LAST-MODIFIED` reflects the new time and its `SEQUENCE` increases
