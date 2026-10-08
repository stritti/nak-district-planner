## Why

District planning and administration currently treat congregations as a flat list, which makes larger districts hard to navigate and compare in planning views. At the same time, creating congregations and districts requires extra steps after creation, slowing setup and causing missing configuration data.

## What Changes

- Add support for assigning congregations to optional groups that can be used for visual grouping in district and planning screens.
- Update the matrix view to support optional secondary sorting/grouping by congregation group while preserving existing date and congregation axes.
- Update district/congregation overview screens to render grouped sections whenever congregations have a group assignment.
- Extend congregation and district creation flows so the create dialog opens with all relevant options directly, reducing post-create edits.

## Capabilities

### New Capabilities
- `congregation-grouping-and-creation-flow`: Manage optional congregation groups and expose grouped visual behavior in matrix and district overview, plus complete option-first create dialogs for congregation/district creation.

### Modified Capabilities


## Impact

- Backend: District/congregation domain and persistence models, validation rules, and API payloads for create/list endpoints.
- Frontend: Matrix planning view, district/congregation overview views, and creation dialog components/forms.
- Data: New optional group relationship/field for congregations and migration/backfill handling for existing records.
