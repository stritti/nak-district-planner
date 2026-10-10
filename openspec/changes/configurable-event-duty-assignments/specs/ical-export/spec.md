## ADDED Requirements

### Requirement: Personal ICS includes organisational duties without duplicates
Personal calendar feeds for an authenticated, securely linked participant or a subject-bound, district-scoped INTERNAL personal export token SHALL include slots assigned through organisational duties, aggregating all of that person's tasks per slot into a single VEVENT. The UID SHALL remain `{planning_slot_id}@nak-bezirksplaner`. A person who is also the service leader SHALL still receive only one VEVENT. Updates to appointments, time and cancellation SHALL be reflected in subsequent feed responses; public or unscoped district INTERNAL exports SHALL not reveal personal duty-holder identities or private duty labels. Export token reads SHALL be limited by the bound subject and district through RLS; existing PUBLIC/INTERNAL leader tokens SHALL retain legacy leader visibility and MUST NOT infer a duty owner from unlinked leader names. No token SHALL be issued for an unlinked free-text name.

#### Scenario: Bound subject token
- **WHEN** a verified user obtains a personal INTERNAL export token bound to their subject for district A
- **THEN** the token reveals only that subject's currently assigned events and duty labels in district A
- **AND** it cannot be used to request another subject or district by query parameter

#### Scenario: Duty-only participant without a leader record
- **WHEN** a securely linked user who has no leader record receives an organisational duty
- **THEN** their authenticated calendar and subject-bound personal ICS include that duty without fabricating a leader record

#### Scenario: Revoked duty or token
- **WHEN** the last qualifying duty is removed or the personal token is revoked
- **THEN** subsequent token reads no longer reveal the removed duty or are rejected for a revoked token

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
