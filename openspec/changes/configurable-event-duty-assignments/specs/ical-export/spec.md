## ADDED Requirements

### Requirement: Personal ICS includes organisational duties without duplicates
Personal calendar feeds for an authenticated participant or their existing appropriately scoped opaque personal token SHALL include slots assigned through organisational duties, aggregating all of that person's tasks per slot into a single VEVENT. The UID SHALL remain `{planning_slot_id}@nak-bezirksplaner`. A person who is also the service leader SHALL still receive only one VEVENT. Updates to appointments, time and cancellation SHALL be reflected in subsequent feed responses; public exports SHALL not reveal personal duties.

#### Scenario: Multiple duties on one slot
- **WHEN** a person has both Organist and Dirigent assignments on one slot
- **THEN** their personal feed contains one VEVENT for the slot and both task labels

#### Scenario: Duty-only personal export
- **WHEN** a person is assigned Schließdienst without a service-leader assignment
- **THEN** their personal feed contains the event with Schließdienst as task

#### Scenario: Cancellation or removal
- **WHEN** a slot is cancelled or the person's last duty assignment is removed
- **THEN** the next feed response follows the established cancellation/removal policy and does not retain a stale personal booking

#### Scenario: Public token
- **WHEN** a PUBLIC export token is used
- **THEN** no personal organisational duty names, assignments or task labels are disclosed
