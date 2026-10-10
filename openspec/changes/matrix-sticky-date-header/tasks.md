## Implementation

- [x] Make the matrix table a bounded, keyboard-focusable two-axis scroll region
- [x] Pin all date headings vertically; pin the top-left corner on both axes with explicit stacking layers
- [x] Preserve holiday and dark-mode backgrounds and the synchronized horizontal scrollbar
- [x] Extend the service-assignment-matrix baseline OpenSpec and provide the delta
- [x] Add component tests for sticky layers, holidays, compact mode and empty dates
- [x] Add browser regression tests for real vertical/horizontal scroll positions, mobile/dark mode and short tables
- [x] Validate frontend unit/E2E tests, lint, coverage gates, and OpenSpec in CI (PR #544)

## Codex review follow-up (PR #544)

- [x] Replace translucent dark holiday heading background with opaque color
- [x] Size proxy scrollbar from matrix client width and cover the last date column
- [x] Restore vertical scroll chaining and cover boundary wheel events
- [x] Add unit/browser regression tests and update OpenSpec baseline, delta and design
- [ ] Verify final CI and coverage on review fix commits
