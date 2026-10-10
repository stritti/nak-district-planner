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
The table SHALL expose editing only for supported mutable event fields and SHALL use their established mutation paths: event properties via scoped event PATCH and responsible-person assignments via the existing assignments API. Authorisation, event scope, status rules, conflict checks, protected external fields and confirmation of destructive actions SHALL be identical to the full editor. Each successful save SHALL update only the intended field/dependent atomic set and refresh the canonical display. Category, congregation and planning-date changes SHALL preserve and flag (not erase) now-ineligible organisational duties and minister appointments according to their dedicated OpenSpec rules. Clearing an assignment that implies deletion SHALL use the existing confirmation workflow.

#### Scenario: Category becomes incompatible with an assigned duty
- **WHEN** a planner changes an event's category and an existing Organist duty is no longer permitted
- **THEN** the duty is retained and flagged for review, rather than silently removed by the field PATCH

#### Scenario: Responsible person changed inline
- **WHEN** an authorised planner changes a responsible-person cell
- **THEN** the application uses the event assignments API with existing conflict handling, not a generic event PATCH

#### Scenario: Forbidden field
- **WHEN** a field is server-managed, external-authoritative or the user lacks permission
- **THEN** it is not inline editable and no write is attempted

### Requirement: Safe asynchronous save and error recovery
The table SHALL show an in-cell saving state, prevent duplicate submissions, and handle 403, 404, validation failures, 409 conflicts and network failures without silently losing the user's draft. Stale or concurrent writes SHALL be prevented by a server-enforced revision precondition (`If-Match` with strong ETag or an existing equivalent explicit version) for every inline mutation. Endpoints without conditional writes SHALL be extended before their columns become inline editable. Missing required revisions SHALL yield 428, mismatches SHALL yield 412, and domain conflicts SHALL continue using 409; the interface SHALL not assert success until the server confirms it.

#### Scenario: Concurrent row changed by another user
- **WHEN** another user saves a newer revision after the inline editor loaded the row
- **THEN** saving with the stale revision is rejected with 412, and the user's draft is preserved for compare/reload rather than blindly overwriting

#### Scenario: No conditional-write contract
- **WHEN** an eligible field has no server-enforced revision precondition
- **THEN** that field is not enabled for inline writing until the backend provides one

#### Scenario: Server conflict
- **WHEN** the server responds with 409 to an inline edit
- **THEN** the cell displays a conflict explanation and retains the proposed value for review or retry, without claiming that it was saved

#### Scenario: Network failure
- **WHEN** saving fails because the network is unavailable
- **THEN** the draft remains available for retry and the old persisted value is not replaced as if saved

#### Scenario: Double submission
- **WHEN** a save is in progress and the user submits the same cell again
- **THEN** at most one request for that mutation remains in flight

### Requirement: Consistent editing across all tabular overviews
Every table, list-style overview and planning matrix in the application SHALL use the same compact read-mode appearance and shared inline-edit interaction for directly mutable, authorised cells. Domain-specific API adapters SHALL preserve existing validations, permission scopes and business workflows. Read-only/derived columns SHALL never become editable merely to achieve consistency. Explicit actions, links, approvals and destructive operations SHALL retain their dedicated semantics and required confirmations.

#### Scenario: Mutable cell in another overview
- **WHEN** an authorised administrator activates a writable field in a non-event table
- **THEN** the same cell activation, saving, cancellation, accessibility and error-handling behaviour applies as in the event overview, using that resource's authorised update API

#### Scenario: Read-only overview
- **WHEN** a user opens a table containing only derived or non-editable data
- **THEN** the table uses the common compact read-only presentation and does not show an editor on cell activation

#### Scenario: Action column or link
- **WHEN** a user activates a row link, selection control or destructive/workflow action
- **THEN** the intended navigation, selection or existing confirmation flow runs without accidentally activating an inline editor

### Requirement: Shared implementation and inventory completeness
The frontend SHALL provide a reusable inline-cell editing component/composable with consistent keyboard, pointer and touch behaviour, focus control and server-feedback states. The implementation SHALL maintain an inventory mapping all table columns to their editability, authorisation and mutation adapter or an explicit read-only exclusion reason. Completing this change SHALL require regression coverage for every inventoried table with writable cells.

#### Scenario: New table adopts shared behaviour
- **WHEN** a new tabular overview introduces an editable column
- **THEN** it uses the shared cell-editing contract instead of a separate editing interaction

#### Scenario: No incomplete migration
- **WHEN** the change is accepted
- **THEN** the inventory shows that every eligible table is integrated and each intentionally excluded table/column has a documented reason
