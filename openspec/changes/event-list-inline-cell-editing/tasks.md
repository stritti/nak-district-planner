## 1. Specification and integration
- [x] 1.1 Inventory event overview columns, actual writable API fields and special workflow actions; record explicit editable field mapping.
- [ ] 1.2 Implement/verify strong ETag `If-Match` (or an existing equivalent explicit server-side version) for every inline mutation, including assignments: 428 missing precondition, 412 stale revision, 409 business conflict; disable editing for endpoints lacking a safe conditional write.
- [ ] 1.3 Validate OpenSpec delta and align other affected canonical specifications.

## 2. Frontend inline editing
- [ ] 2.1 Implement compact read-only cell rendering, full-value access and clear edit affordance on focus.
- [ ] 2.2 Implement one-cell editor state machine, click/Enter/F2 activation, Escape cancellation, Enter/Tab/Shift+Tab save/navigation and blur semantics.
- [ ] 2.3 Implement field-specific widgets, client validation, accessible feedback and responsive/touch editor.
- [ ] 2.4 Connect event PATCH and responsible-person assignment endpoints while retaining existing conflict, permission and confirmation policies.
- [ ] 2.5 Handle async save, retries, race conditions, refresh, sorting/filter changes and stale row data.

## 3. Verification
- [ ] 3.1 Unit and component tests: read mode, editor activation, keyboard/focus, empty/long values, permissions and no accidental edits.
- [ ] 3.2 API interaction tests: successful save, validation failure, 403, 404, 409, 412, 428, network failure, retry, double submit, stale response and concurrent edits.
- [ ] 3.3 Regression tests: leader conflicts, protected fields, cancelled events, external events, category/congregation changes that invalidate duties, minister service-end-date checks, removal confirmation, filters/sorting and responsive behaviour.
- [ ] 3.4 Run frontend tests, lint, build and OpenSpec validation; maintain >80% coverage with edge-path coverage.

## 4. Cross-application consistency
- [x] 4.1 Inventory every Vue table, overview, list and planning matrix; record each column's editable/read-only/action classification, role and backend mutation endpoint.
- [x] 4.2 Extract a reusable Vue inline-cell editor/composable with standard compact display, keyboard/touch activation, focus management, mutation lifecycle and accessible errors.
- [ ] 4.3 Migrate all eligible mutable table cells throughout the application to the shared interaction; retain domain-specific save adapters and validations.
- [ ] 4.4 Bring read-only/derived/externally managed and action-only tables into consistent display styling without offering unauthorised edits or bypassing confirmation dialogs.
- [ ] 4.5 Cover every inventoried table with integration regression tests for editability, authorisation, keyboard operation, async failure/retry and sorting/pagination where applicable.
- [ ] 4.6 Document any excluded table or column with an explicit reason, and ensure no eligible overview remains on a competing inline-edit interaction.


## Implementation progress (PR #576)

A conditional-write adapter and reusable editor are integrated for internal event titles only.
The full event and cross-application scope remains open: assignment preconditions,
domain-dependent changes and administrative list updates are not yet covered.
See [table inventory](./table-inventory.md) for explicit deferred columns and reasons.

## Delivery split and acceptance gate (2026-10-14)

- **PR #576 (foundation):** Shared inline editor, event title and leader contact/name conditional writes. This PR is not the completion of this OpenSpec change. General legacy PATCH writers still need end-to-end conditional-write enforcement; the review remains open until every modal writer and backend contract participates. Focus, responsive keyboard navigation, permission hierarchy and refresh-failure recovery require passing regression tests.
- **PR #577 (matrix):** Implement scoped responsible-person and organisational-duty assignment mutation contracts, conditional revisions (428/412), existing 409 acknowledgement and deletion confirmation, keyboard/touch UI and regression tests. Currently a planning draft.
- **PR #578 (dependent event changes):** Implement atomic planning date/time, category and congregation changes with duty invalidation review, old-congregation private-assignment quarantine and minister service-end checks. Currently a planning draft.
- **Remaining cross-application tranche:** Classify and migrate other eligible leader-administration fields and read-only tabular surfaces; verify accessible compact display and screen-by-screen keyboard, sorting and filtering regressions. This scope is not automatically covered by PRs #577 or #578 and must be tracked explicitly.

**Acceptance:** Do not check off 1.2, 2.4-2.5, 3.1-3.4 or 4.3-4.6 until corresponding code, edge-case tests, OpenSpec validation and CI coverage over 80% are verified on their actual PR heads. A green foundation CI alone does not complete the change.


## Implementation progress (release 1.1.x review branch)

- Event list **Start** column is inline editable through the shared cell (`inputType="datetime-local"`)
  and `useInlineScheduleSave`: conditional `PATCH` (428/412), duration preserved, single explicit
  WARN confirmation, BLOCK/412 keep the draft. Covered by composable and view regression tests.
- **Responsible** column integrated in PR #577; the inventory was stale and has been corrected.
- **Category** and **Zuordnung (congregation)** inline: backend `change-impact` preview now reports
  duties that would newly need review or be quarantined (`EventDutiesService.preview_scope_change`);
  the frontend (`useInlineScopeSave`) previews, confirms once, then patches conditionally.
- Still open (not checked off): mobile start/category/congregation editing, leader administration remaining fields, and the per-table
  regression sweep of 4.5/4.6. Tasks 1.2, 2.4, 3.x and 4.3-4.6 therefore stay unchecked per the acceptance gate above.
