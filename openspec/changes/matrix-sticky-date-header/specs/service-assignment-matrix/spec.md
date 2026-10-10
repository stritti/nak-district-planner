## ADDED Requirements
### Requirement: Sticky matrix date headings
The matrix SHALL keep weekday, date and holiday headings visible at the top during vertical scrolling in its bounded two-axis scroll region. Congregation names SHALL remain pinned to the left. The top-left corner SHALL stay above both axes, with opaque header backgrounds in light, dark and compact modes.

#### Scenario: Two-axis matrix scrolling
- **WHEN** the user scrolls a tall and wide matrix vertically and horizontally
- **THEN** weekday, date and holiday headings stay at the top of the matrix scroll region, congregation names stay at the left, and the top-left corner stays visible above both

#### Scenario: Short or empty matrix
- **WHEN** the matrix has fewer rows than the available space or no date columns
- **THEN** the view SHALL NOT force unnecessary vertical scrolling or render an empty sticky header
