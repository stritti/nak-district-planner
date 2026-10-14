## Why

The congregation column stays visible during horizontal navigation, but date headings scroll away when the matrix is tall. Users then lose the day/date context for assignments (Issue #543).

## What Changes

- Keep weekday, date and holiday headers visible while scrolling the matrix vertically.
- Preserve the existing pinned congregation column and horizontally synchronized scrollbar.
- Make the top-left corner sticky in both directions with predictable layering.
- Use a bounded two-axis scroll region rather than relying on `position: sticky` inside a horizontally scrolling ancestor during document scrolling.

## Capabilities

### Modified Capabilities

- `service-assignment-matrix`: Matrix usability with a sticky date header and intersection cell.

## Impact

- Vue matrix table layout, unit tests, browser E2E tests and OpenSpec baseline.
- No backend, database, API, or new dependencies.
