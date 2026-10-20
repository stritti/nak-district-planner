## ADDED Requirements

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

#### Scenario: Unusable leader
- **WHEN** the leader is unknown, belongs to another district, is inactive, hidden or retired before the event
- **THEN** the API answers as for any unknown reference (404) and saves nothing

#### Scenario: Duty and service at the same time
- **WHEN** the leader leads a service at an overlapping event, in this or another congregation
- **THEN** the duty is blocked with a `duty_double_booking` conflict

#### Scenario: Several identities
- **WHEN** a request names more than one of name, account and leader, or a name suggestion together with a leader
- **THEN** the request is rejected by validation

