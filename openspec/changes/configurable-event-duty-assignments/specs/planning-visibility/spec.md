## ADDED Requirements

### Requirement: Organisational duty assignees receive personal event visibility
A person assigned an organisational duty SHALL see the corresponding planning slot in their personal calendar, including slots on which they are not liturgical service leader. Existing visibility, cancellation, confirmed-status and distribution rules SHALL remain applicable to public and congregation views. The system SHALL not disclose task assignees through anonymous or public calendar data.

#### Scenario: Person only holds an organisational duty
- **WHEN** a person is assigned as Organist on an eligible active planning slot but is not its service leader
- **THEN** that person can see the slot and their Organist responsibility in their personal calendar

#### Scenario: Duty removed
- **WHEN** the person's only assignment to a slot is removed
- **THEN** the slot no longer appears by virtue of that removed duty in their personal calendar

#### Scenario: Public calendar privacy
- **WHEN** an unauthenticated visitor requests a public feed
- **THEN** the feed exposes neither duty-holder identity nor personal task details
