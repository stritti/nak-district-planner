## 1. Backend Data Model and API

- [x] 1.1 Add district-scoped congregation group persistence model and migration (new group table and nullable congregation group reference).
- [x] 1.2 Update domain/application validation to enforce same-district group assignment for congregation create/update flows.
- [x] 1.3 Extend district/congregation API schemas and endpoints to expose optional group metadata in list/detail responses.
- [x] 1.4 Extend congregation create/update request handling to accept optional group assignment while remaining backward compatible.

## 2. Matrix and Overview Grouped Presentation

- [x] 2.1 Add frontend data mapping for congregation groups in district/congregation overview state.
- [x] 2.2 Implement grouped section rendering in district/congregation overview with a dedicated ungrouped bucket.
- [x] 2.3 Add matrix toggle/control for optional grouping-based secondary sorting.
- [x] 2.4 Implement matrix ordering logic for group-first then existing congregation order, preserving current default order when grouping is off.

## 3. Creation Dialog Enhancements

- [x] 3.1 Refactor district creation dialog to present full creation-time option set in the initial modal.
- [x] 3.2 Refactor congregation creation dialog to present full creation-time option set including optional group selection.
- [x] 3.3 Ensure form validation and payload mapping support all exposed options without requiring immediate follow-up edits.

## 4. Verification and Rollout Safety

- [x] 4.1 Add/update backend tests for group assignment validation, cross-district rejection, and optional null-group creation.
- [x] 4.2 Add/update frontend tests for grouped overview rendering and matrix grouped-sorting toggle behavior.
- [x] 4.3 Add migration and deployment notes for additive rollout and fallback behavior with null group assignments.
