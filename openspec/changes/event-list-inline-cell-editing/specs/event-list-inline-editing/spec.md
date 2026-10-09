## ADDED Requirements

### Requirement: Compact read-only event table by default
The event overview SHALL display event data as a compact, legible table with formatted text in cells, without always-visible input controls. The full value of truncated text SHALL remain accessible. Non-editable and read-only fields SHALL not present an edit affordance.

#### Scenario: Normal overview
- **WHEN** a user loads the event overview without interacting with a cell
- **THEN** rows show compact formatted text, including clear empty values, without inputs occupying table space

#### Scenario: Long field value
- **WHEN** a displayed value exceeds available column width
- **THEN** the cell stays compact and the complete value remains accessible to keyboard and pointer users

### Requirement: Explicit activation of a cell editor
An editable cell SHALL enter edit mode only after deliberate pointer activation or keyboard Enter/F2 on its focused cell. Only one cell SHALL be edited at a time; activating another editable cell SHALL first resolve the active draft through the defined save or cancel flow. The editor SHALL receive focus and be labelled by its event row and column. A touch device SHALL be usable without hover.

#### Scenario: Click to edit
- **WHEN** an authorised planner clicks an editable title cell
- **THEN** an appropriate text control replaces the formatted value in that cell and receives focus

#### Scenario: Viewer attempts activation
- **WHEN** a viewer clicks or presses Enter on a non-writable cell
- **THEN** the table remains in read mode and no mutation request is made

### Requirement: Predictable commit and cancellation
The editor SHALL validate the draft and commit a changed value with Enter, Tab, Shift+Tab or outside click/blur. Tab/Shift+Tab SHALL move to the next/previous writable cell after a successful save. Escape SHALL discard uncommitted changes and restore the previous value without an API call. Unchanged values SHALL NOT trigger mutations. Failed validation or persistence SHALL preserve the draft, report the issue and prevent silent navigation loss.

#### Scenario: Escape cancels
- **WHEN** the planner changes a value and presses Escape before saving
- **THEN** the last persisted value is displayed and no update is sent

#### Scenario: Keyboard navigation
- **WHEN** an edited cell is saved successfully with Tab
- **THEN** focus advances to the next writable cell according to table order

#### Scenario: Invalid edit
- **WHEN** a draft fails local or server validation
- **THEN** the cell remains editable, the validation error is visible and the draft is preserved

### Requirement: Field-specific, authorised mutation
The table SHALL expose editing only for supported mutable event fields and SHALL use their established mutation paths: event properties via scoped event PATCH and responsible-person assignments via the existing assignments API. Authorisation, event scope, status rules, conflict checks, protected external fields and confirmation of destructive actions SHALL be identical to the full editor. Each successful save SHALL update only the intended field/dependent atomic set and refresh the canonical display.

#### Scenario: Responsible person changed inline
- **WHEN** an authorised planner changes a responsible-person cell
- **THEN** the application uses the event assignments API with existing conflict handling, not a generic event PATCH

#### Scenario: Forbidden field
- **WHEN** a field is server-managed, external-authoritative or the user lacks permission
- **THEN** it is not inline editable and no write is attempted

### Requirement: Safe asynchronous save and error recovery
The table SHALL show an in-cell saving state, prevent duplicate submissions, and handle 403, 404, validation failures, 409 conflicts and network failures without silently losing the user's draft. Stale or concurrent writes SHALL be detected or resolved through an explicit conditional-write strategy before overwrite; the interface SHALL not assert success until the server confirms it.

#### Scenario: Server conflict
- **WHEN** the server responds with 409 to an inline edit
- **THEN** the cell displays a conflict explanation and retains the proposed value for review or retry, without claiming that it was saved

#### Scenario: Network failure
- **WHEN** saving fails because the network is unavailable
- **THEN** the draft remains available for retry and the old persisted value is not replaced as if saved

#### Scenario: Double submission
- **WHEN** a save is in progress and the user submits the same cell again
- **THEN** at most one request for that mutation remains in flight
