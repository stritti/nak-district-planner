## ADDED Requirements
### Requirement: Sticky matrix date headings
The matrix SHALL keep weekday, date and holiday headings visible at the top during vertical scrolling in its bounded two-axis scroll region. Congregation names SHALL remain pinned to the left. The top-left corner SHALL stay above both axes, with opaque header backgrounds in light, dark and compact modes.

#### Scenario: Two-axis matrix scrolling
- **WHEN** the user scrolls a tall and wide matrix vertically and horizontally
- **THEN** weekday, date and holiday headings stay at the top of the matrix scroll region, congregation names stay at the left, and the top-left corner stays visible above both

#### Scenario: Opaque holiday header in dark mode
- **WHEN** a holiday date header is sticky while the matrix scrolls in dark mode
- **THEN** its background SHALL be fully opaque so underlying cell content cannot show through

#### Scenario: Vertical overscroll at the matrix boundary
- **WHEN** the user scrolls beyond the first or last matrix row
- **THEN** the scroll gesture SHALL continue into the surrounding document without trapping vertical page navigation

#### Scenario: Short or empty matrix
- **WHEN** the matrix has fewer rows than the available space or no date columns
- **THEN** the view SHALL NOT force unnecessary vertical scrolling or render an empty sticky header

## MODIFIED Requirements

### Requirement: Pinned horizontal scrollbar
When the matrix is wider than its container, its horizontal scrollbar SHALL stay at the bottom edge of the visible viewport, even while the table extends further down, and SHALL stay in sync with the table's horizontal scroll position. The proxy SHALL cover the full scroll range, including when a classic vertical scrollbar reduces the matrix's usable width.

#### Scenario: Tall and wide matrix on a small screen
- **WHEN** the matrix is wider and taller than the viewport
- **THEN** the horizontal scrollbar is visible at the bottom of the viewport without scrolling to the end of the table

#### Scenario: Classic vertical scrollbar consumes content width
- **WHEN** a non-overlay vertical scrollbar reduces the matrix client width
- **THEN** the horizontal proxy viewport SHALL match the matrix client width and reach the complete rightmost date column
