## Why

A new district reaches an empty matrix twice: before it has congregations and before any services are planned. Both empty states only pointed elsewhere, so the planner had to find the right dialog or the draft generation in the filters on their own.

## What Changes

- "Gemeinde anlegen" in the empty matrix opens the new-congregation dialog of that district directly (`/admin/districts?new=congregation&district=<id>`).
- A matrix with congregations but no planned services explains the next step and offers planners "Entwürfe erzeugen" for the shown range.

## Impact

- Frontend only: `MatrixTable.vue`, `DistrictsAdminView.vue`; uses the existing draft generation endpoint and its permission check.
