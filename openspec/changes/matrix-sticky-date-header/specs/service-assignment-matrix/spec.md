## MODIFIED Requirements

### Requirement: Matrix usability
The matrix view SHALL show a skeleton while loading, keep the congregation column sticky during horizontal scroll, and keep all date headings (weekday, date and holiday names) sticky during vertical scroll within a viewport-bounded matrix scroll region. The top-left congregation heading SHALL remain fixed on both axes above date and congregation cells. Sticky headings SHALL have opaque backgrounds in light/dark and compact modes. The matrix SHALL offer a congregation text filter and an optional group-based secondary sort, and mark external time deviations with an indicator.

#### Scenario: Group sorting enabled
- **WHEN** the user enables group sorting
- **THEN** congregations are ordered by group and then by their existing order

#### Scenario: Two-axis matrix scrolling
- **WHEN** the user scrolls a tall and wide matrix vertically and horizontally
- **THEN** weekday, date and holiday headings stay at the top of the matrix scroll region, congregation names stay at the left, and the top-left corner stays visible above both

#### Scenario: Short or empty matrix
- **WHEN** the matrix has fewer rows than the available space or no date columns
- **THEN** the view SHALL NOT force unnecessary vertical scrolling or render an empty sticky header
