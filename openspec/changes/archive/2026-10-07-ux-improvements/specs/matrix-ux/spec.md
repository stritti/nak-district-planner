## ADDED Requirements

### Requirement: Matrix skeleton loading screen
The system SHALL display an animated skeleton screen while the matrix data is loading.

#### Scenario: Matrix loading
- **WHEN** the matrix view is loading data
- **THEN** the system SHALL display placeholder rows with a pulse animation
  instead of a plain loading text

### Requirement: Matrix sticky congregation column
The system SHALL keep the congregation name column visible during horizontal scrolling.

#### Scenario: Horizontal scroll
- **WHEN** the user scrolls horizontally in the matrix table
- **THEN** the first column (congregation name) SHALL remain fixed on the left side

### Requirement: Matrix scroll indicators
The system SHALL indicate that the matrix table is horizontally scrollable.

#### Scenario: Scrollable content exists
- **WHEN** the matrix table content exceeds the visible area horizontally
- **THEN** a shadow or visual indicator SHALL be shown at the right edge

### Requirement: Matrix congregation filter
The system SHALL allow filtering the matrix rows by congregation name.

#### Scenario: Filter applied
- **WHEN** the user enters text in the congregation filter field
- **THEN** only rows whose congregation name matches the filter SHALL be visible
- **AND** the filtering SHALL be performed client-side without additional API requests
