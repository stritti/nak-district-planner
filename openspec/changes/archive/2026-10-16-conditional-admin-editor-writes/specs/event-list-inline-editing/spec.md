## MODIFIED Requirements

### Requirement: Dialog writers honour the same revision contract
Every writer of a field that is also editable inline SHALL be conditional on the same server revision, so a dialog or legacy writer cannot silently overwrite an inline change. This covers event updates, assignment create/update/delete (event revision), leader updates, renames of districts and groups, congregation dialog edits, reminder-configuration and event-hook updates (including their active switches) and changes of organisational duty assignments and suggestions.

#### Scenario: Dialog save after an inline change
- **WHEN** an assignment is changed inline and a dialog that was opened earlier then saves the same assignment
- **THEN** the server rejects the dialog write with 412 and the dialog explains that the event changed meanwhile

#### Scenario: Write without a precondition
- **WHEN** a client sends an assignment write or a district or group rename without `If-Match`
- **THEN** the server answers 428 and nothing is changed

#### Scenario: Dialog retains the revision it was opened with
- **WHEN** a matrix dialog or the event editor saves an assignment
- **THEN** it sends the revision read with the cell or returned by the preceding event update, never a later or empty one

#### Scenario: Rows without a modification timestamp
- **WHEN** an organisational duty assignment or a name suggestion is changed
- **THEN** its revision is derived from the row content, so any concurrent change to the row invalidates an earlier revision
- **AND** creating a new assignment remains unconditional because there is no prior state to protect
