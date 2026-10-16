## ADDED Requirements

### Requirement: Inline responsible-person editing uses existing assignment semantics
When the event overview allows editing its responsible-person column in place, the system SHALL use the existing `/api/v1/events/{event_id}/assignments` flow, including status updates, conflicting appointments and required warning acknowledgements. A failed mutation SHALL not make the event list display the proposed person as confirmed.

#### Scenario: Assignment conflict from inline editor
- **WHEN** a planner selects a conflicting service leader in an inline cell editor
- **THEN** the existing 409 conflict policy applies and the current persisted assignment remains displayed until successfully changed
