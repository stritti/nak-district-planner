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
