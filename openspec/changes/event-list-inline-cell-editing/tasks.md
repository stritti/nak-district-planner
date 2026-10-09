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

## 4. Cross-application consistency
- [ ] 4.1 Inventory every Vue table, overview, list and planning matrix; record each column's editable/read-only/action classification, role and backend mutation endpoint.
- [ ] 4.2 Extract a reusable Vue inline-cell editor/composable with standard compact display, keyboard/touch activation, focus management, mutation lifecycle and accessible errors.
- [ ] 4.3 Migrate all eligible mutable table cells throughout the application to the shared interaction; retain domain-specific save adapters and validations.
- [ ] 4.4 Bring read-only/derived/externally managed and action-only tables into consistent display styling without offering unauthorised edits or bypassing confirmation dialogs.
- [ ] 4.5 Cover every inventoried table with integration regression tests for editability, authorisation, keyboard operation, async failure/retry and sorting/pagination where applicable.
- [ ] 4.6 Document any excluded table or column with an explicit reason, and ensure no eligible overview remains on a competing inline-edit interaction.
