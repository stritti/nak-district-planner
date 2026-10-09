## Why

Planning slots already support a single liturgical service-leader assignment, but do not model the independent organisational duties needed at worship services and other events. Congregations and districts need configurable roles such as Schließdienst, Organist and Dirigent, and assigned participants must see their responsibilities in their personal calendars.

## What Changes

- Add an independently configurable organisational duty catalogue at district and congregation scope, with event-category applicability and explicit congregation overrides.
- Seed default duty categories for Gottesdienst (Schließdienst, Organist, Dirigent) and every other event category (Schließdienst only). All assignments are optional.
- Allow zero or more user/person assignments to configured duties on PlanningSlots, without changing the existing single service-leader assignment.
- Show assigned duties in event editing and in each assignee's personal calendar and personal ICS export. Keep public feeds free of personal duty data.
- Preserve historical assignments after catalogue changes, and enforce tenant isolation and scoped authorisation.

## Capabilities

### New Capabilities
- `event-duty-categories`: district/congregation configuration, inheritance, defaults and category lifecycle.
- `event-duty-assignments`: optional, validated duty assignment to planning slots.
- `duty-name-suggestions`: duty-specific remembered free-text names and reversible suppression.
- `minister-lifecycle`: deactivation, hidden historical records and dated planning eligibility.

### Modified Capabilities
- `planning-visibility`: assigned organisational duties in personal calendars only.
- `ical-export`: stable per-event personal calendar projection of organisational duties.

## Impact

- Backend: domain and persistence models, Alembic migration, scoped REST APIs, validation, query logic and tests.
- Frontend: district/congregation settings, event duty assignment editor, personal calendar and tests.
- Existing `PlanningSlot`/`EventInstance`, service-leader assignments, visibility and calendar feed policies remain authoritative.
- No automatic booking or changes to the liturgical leader assignment.

## Non-goals

- Shift scheduling, automatic candidate selection, reminders or acceptance workflows.
- Introducing external calendar provider write-back.
- Retroactively adding people to existing events.

## Further requirements: remembered duty names and retired ministers

- Allow direct entry of a person's display name for organisational duties, remembering accepted names as scope- and duty-type-specific autocomplete suggestions for future events, without requiring a user account.
- Allow authorised users to remove a name from autocomplete suggestions without erasing historical duty appointments.
- Allow ministers/service leaders to be deactivated and hidden from default frontend lists while retaining database records and all historical references; provide an optional inclusive end-of-service date respected by future planning and assignments.
