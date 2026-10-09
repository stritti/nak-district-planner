## 1. Specification and integration
- [ ] 1.1 Inventory event overview columns, actual writable API fields and special workflow actions; record explicit editable field mapping.
- [ ] 1.2 Verify authoritative PATCH/assignment contracts, conflict handling and optimistic concurrency; specify backend extension only if required.
- [ ] 1.3 Validate OpenSpec delta and align other affected canonical specifications.

## 2. Frontend inline editing
- [ ] 2.1 Implement compact read-only cell rendering, full-value access and clear edit affordance on focus.
- [ ] 2.2 Implement one-cell editor state machine, click/Enter/F2 activation, Escape cancellation, Enter/Tab/Shift+Tab save/navigation and blur semantics.
- [ ] 2.3 Implement field-specific widgets, client validation, accessible feedback and responsive/touch editor.
- [ ] 2.4 Connect event PATCH and responsible-person assignment endpoints while retaining existing conflict, permission and confirmation policies.
- [ ] 2.5 Handle async save, retries, race conditions, refresh, sorting/filter changes and stale row data.

## 3. Verification
- [ ] 3.1 Unit and component tests: read mode, editor activation, keyboard/focus, empty/long values, permissions and no accidental edits.
- [ ] 3.2 API interaction tests: successful save, validation failure, 403, 404, 409, network failure, retry, double submit, stale response and concurrent edits.
- [ ] 3.3 Regression tests: leader conflicts, protected fields, cancelled events, external events, filters/sorting and responsive behaviour.
- [ ] 3.4 Run frontend tests, lint, build and OpenSpec validation; maintain >80% coverage with edge-path coverage.
