## ADDED Requirements

### Requirement: Organisational duty assignees receive personal event visibility
A securely verified registered user linked as an organisational duty assignee SHALL see the corresponding planning slot in their authenticated personal calendar, including slots on which they are not liturgical service leader. Existing visibility, cancellation, confirmed-status and distribution rules SHALL remain applicable to public and congregation views. Assignments quarantined after a congregation move SHALL NOT become visible in the destination's ordinary event or personal feeds before authorised revalidation. Name-only participants and unlinked leader records SHALL NOT gain personal calendar eligibility through duty text; the authenticated view SHALL apply the linked subject's current memberships, and each token-based personal view SHALL remain district-scoped. The system SHALL not disclose task assignees through anonymous or public calendar data.

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
