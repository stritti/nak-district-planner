## ADDED Requirements

### Requirement: Published cancellations remain exported
A slot that has ever been released SHALL remain in applicable calendar exports when cancelled, with stable identity. Published slots SHALL NOT become undeletable drafts by lowering approval. A never-published deleted slot SHALL be absent from all exports.

#### Scenario: Cancellation of a published event
- **WHEN** a planner cancels an already confirmed event
- **THEN** subsequent ICS feeds expose the same event UID and `STATUS:CANCELLED`; XLSX event exports include `Abgesagt`

#### Scenario: Draft removed
- **WHEN** a never-confirmed draft is deleted
- **THEN** no future event list or export includes the deleted slot
