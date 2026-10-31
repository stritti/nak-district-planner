## ADDED Requirements

### Requirement: Getting-started checklist
The SPA SHALL show users who plan at least one district a start page at `/` with the setup steps of the selected district in order: district, congregations with service times, leaders, service drafts, leader assignments, release and calendar subscription. Each step SHALL show its status, link its page and offer its action only to roles allowed to take it. Draft, assignment and release status SHALL cover the next four weeks. Users without a planning role SHALL be sent to the event list.

#### Scenario: Next open step
- **WHEN** a planner opens `/` and the selected district has services with gaps in the next four weeks
- **THEN** the steps up to the drafts are shown as done
- **AND** the assignment step is highlighted with the number of gaps and a link to the matrix

#### Scenario: Step of another role
- **WHEN** a planner who is not a district admin opens the start page
- **THEN** the leader and calendar-subscription steps show who takes them instead of an action
- **AND** the calendar subscriptions are not requested

#### Scenario: Unavailable status
- **WHEN** the request for one step's status fails
- **THEN** that step is shown as unknown and the other steps keep their status

#### Scenario: Viewer
- **WHEN** a user without a planning role opens `/`
- **THEN** the SPA shows the event list
