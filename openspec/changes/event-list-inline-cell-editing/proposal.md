## Why

The event overview currently requires more interaction than necessary to update individual fields. Planners need spreadsheet-like inline editing while retaining a dense, readable table when they are not editing.

## What Changes

- Display event rows as compact, read-only text by default. Editing controls render only when an editable cell is activated by click or keyboard.
- Save validated cell updates individually with predictable Enter, Escape, Tab and blur behaviour, explicit pending/error feedback and safe retry.
- Reuse existing event update and service-leader assignment APIs, authorisation and conflict handling rather than bypassing domain invariants.
- Make the interaction keyboard accessible and touch friendly; support efficient navigation without enabling unintentional edits.
- Keep the event table filters, sorting, pagination and responsive layout intact.

## Capabilities

### New Capabilities
- `event-list-inline-editing`: compact spreadsheet-like table cell editing, validation, persistence, accessibility and errors.

### Modified Capabilities
- `frontend-ux`: edit-in-place interaction and feedback.
- `service-assignment-matrix`: existing event-list responsible-person cell uses shared assignment API and conflict handling.

## Impact

Frontend event overview and tests are primary. Backend changes only if needed to support field-level optimistic concurrency or validation consistently. No new writable fields, no bypass of PlanningSlot/EventInstance separation, and no changes to existing permissions.

## Non-goals

- Bulk paste/fill, spreadsheet formulas or multi-cell transactions.
- Editing historical read-only metadata or external provider-controlled fields.
- Replacing the existing full event details/editor for complex operations.
