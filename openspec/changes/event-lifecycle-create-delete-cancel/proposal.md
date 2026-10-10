## Why

The events overview supports only reading and editing existing planning slots. Planners cannot manually add an event or remove an unpublished draft. Removing an already released event would silently remove its stable calendar UID from subscribed feeds, leaving calendar users with stale appointments.

## What Changes

- Add `POST /api/v1/events` to create an INTERNAL event with a planning slot and occurrence, initially `PLANNED` and `ACTIVE`.
- Add `DELETE /api/v1/events/{id}` only for events which have never been published; the server returns 409 for released events, including formerly published ones.
- Persist `released_at` as an irreversible first-publication marker, backfilled from existing confirmed events.
- Prevent single-event and monthly unpublication and reopening published cancellations.
- Keep released events when a linked external calendar or invitation is deleted; mark them `CANCELLED` instead of hard deletion even under the provider's `HARD_DELETE` policy.
- Render creation and deletion actions in the event overview, with explicit confirmation before draft deletion.
- Keep ICS stable UIDs with `STATUS:CANCELLED`; represent cancellations in XLSX using the existing `Abgesagt` label.

## Impact

- Specs: `planning-model`, `planning-visibility`, `ical-export`.
- API: `POST /api/v1/events`, `DELETE /api/v1/events/{id}`, new `was_released` response flag.
- DB: `planning_slots.released_at` with Alembic backfill.
- Backend: domain, repository, router, calendar sync and invitations.
- Frontend: typed API client, create modal, guarded delete action, existing edit form.
- Tests: API, repository, frontend and sync regression cases.
