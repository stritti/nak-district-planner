## Why

Issue #466: the matrix (UC-03), the congregation event view (UC-04) and the ICS
export (UC-05) each decided on their own which planning slots a congregation or
feed may see. The rules diverged: cancelled slots showed up as red LÜCKE and
hid active slots, district slots appeared in every matrix row, PLANNED drafts
leaked into congregation views and PUBLIC feeds, congregation feeds missed
distributed district events, personal leader feeds contained the whole district,
and cancelled slots were exported as normal events.

## What Changes

- One pure domain predicate, `PlanningSlot.is_visible_to(congregation_id)`
  (own slot, or district slot whose `applicability` lists the congregation or
  `"all"`; an empty list means "not distributed"), plus `is_confirmed` /
  `is_distributed_to(congregation_id)` for the approval policy.
- `ExportToken.confirmed_only(requested)`: PUBLIC tokens always export only
  CONFIRMED slots; `?approval_status` can no longer widen them. INTERNAL tokens
  (including personal leader feeds) keep the parameter and default to including
  PLANNED slots (marked `STATUS:TENTATIVE`).
- Matrix: only ACTIVE slots; district slots only in rows of applicable
  congregations; an own slot wins over a district slot, earliest time first.
- Congregation event view: district slots only when ACTIVE and CONFIRMED.
- ICS export: congregation feeds include district slots released to the
  congregation; leader feeds only that leader's slots; CANCELLED slots are
  emitted with `STATUS:CANCELLED` so subscribed calendars remove them;
  `DTSTAMP`/`LAST-MODIFIED` from the last revision of slot, event instance,
  displayed leader and congregation; `SEQUENCE` = seconds since 2020 of that
  revision (monotonic, within the 32-bit RFC 5545 INTEGER). UIDs remain `{slot_id}@nak-bezirksplaner`.
- Frontend: the planned/confirmed toggle is shown for INTERNAL tokens only.

This change supersedes the outdated event-distribution wording of
`uc-04-05-06-event-export-feiertage` (`events.applicability`, `status=PUBLISHED`
/ `DRAFT`): distribution is now defined on `PlanningSlot` with
`status=ACTIVE` and `approval_status=CONFIRMED`.

## Capabilities

### New Capabilities
- `planning-visibility`

### Modified Capabilities
- `event-distribution` (superseded wording, see above)
- `ical-export`
- `service-matrix`

## Impact

- Backend: `app/domain/models/planning_slot.py`, `app/domain/models/export_token.py`,
  routers `districts.py` (matrix), `events.py`, `export.py`.
- Frontend: `ExportTokensView.vue`.
- No schema migration; response shapes unchanged.
- Behaviour change: district slots without `applicability` no longer appear in
  matrix rows; district slots without `approval_status=CONFIRMED` are not
  distributed to congregation views or congregation feeds.
- Imported holidays (`category=Feiertag`) are reference data: `feiertage_service`
  creates them with `approval_status=CONFIRMED`, and data migration
  `20261007_confirm_holidays` sets CONFIRMED on existing holiday slots (downgrade
  is a documented no-op), so referenced holidays stay visible to congregations.
