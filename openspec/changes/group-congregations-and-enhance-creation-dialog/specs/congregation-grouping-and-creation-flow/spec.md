## ADDED Requirements

### Requirement: Congregations SHALL support optional district-scoped group assignment
The system SHALL allow each congregation to be assigned to zero or one district-scoped congregation group. The system MUST validate that an assigned group belongs to the same district as the congregation.

#### Scenario: Create congregation without group assignment
- **WHEN** a user creates a congregation and does not provide a group
- **THEN** the congregation is created successfully with no group assignment

#### Scenario: Create congregation with valid district group
- **WHEN** a user creates a congregation and provides a group identifier from the same district
- **THEN** the congregation is created successfully and linked to that group

#### Scenario: Reject cross-district group assignment
- **WHEN** a user creates or updates a congregation with a group identifier that belongs to a different district
- **THEN** the system rejects the request with a validation error

### Requirement: District and congregation overviews SHALL render grouped congregation sections
The system SHALL present congregations grouped by assigned group in district/congregation overview screens whenever at least one congregation in scope has a group assignment. Ungrouped congregations MUST remain visible in a dedicated ungrouped section.

#### Scenario: Grouped overview rendering
- **WHEN** overview data contains congregations assigned to multiple groups
- **THEN** the UI renders separate sections per group and lists each congregation under its group

#### Scenario: Mixed grouped and ungrouped rendering
- **WHEN** overview data contains both grouped and ungrouped congregations
- **THEN** the UI renders grouped sections and an ungrouped section in the same view

### Requirement: Matrix view SHALL provide optional grouping-based secondary sorting
The matrix view SHALL provide a user-selectable mode that applies grouping-based secondary sorting for congregations. In this mode, congregations MUST be ordered by group and then by existing congregation order within each group. If grouping mode is not selected, existing ordering SHALL remain unchanged.

#### Scenario: Default matrix order unchanged
- **WHEN** a user opens the matrix without enabling grouping mode
- **THEN** congregation ordering matches the existing non-grouped behavior

#### Scenario: Grouping mode enabled
- **WHEN** a user enables grouping-based sorting in matrix view
- **THEN** congregations are displayed in grouped order with stable intra-group ordering

### Requirement: District and congregation creation dialogs SHALL expose full initial option set
The system SHALL present district and congregation creation dialogs with all supported creation-time options in the initial dialog so users can complete setup without an immediate follow-up edit step.

#### Scenario: District create dialog includes full options
- **WHEN** a user opens the district create dialog
- **THEN** all district creation options defined by the API are available before submission

#### Scenario: Congregation create dialog includes full options including group
- **WHEN** a user opens the congregation create dialog
- **THEN** all congregation creation options, including optional group assignment, are available before submission
