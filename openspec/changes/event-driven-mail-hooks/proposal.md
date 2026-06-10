## Why

The planning workflow is not just about scheduled reminders (day X of month). Critical situations arise asynchronously throughout the month — a service slot remains unassigned (LÜCKE), a new external event is detected and needs review, a sync job fails, a registration comes in. Currently these events have no outbound notification channel. Administrators must actively poll the system.

Now that a MailService infrastructure exists (see `configurable-email-reminders`), the next step is to make the system react to its own events — sending context-aware emails when governance-relevant situations occur.

## What Changes

- New domain entity `EventMailHook` — per-district configuration that maps a system event type to an email notification (recipient role, subject template, body template)
- Lightweight event-bus mechanism — domain events emitted by existing services are consumed by a hook evaluator that matches them against active hooks and dispatches via MailService
- Pre-defined event types for initial release:
  - `SLOT_UNASSIGNED` — A planning slot without service assignment (LÜCKE was detected)
  - `EXTERNAL_EVENT_DETECTED` — A new external event candidate is awaiting review
  - `SYNC_ERROR` — A calendar sync job failed
  - `REGISTRATION_RECEIVED` — A new leader registration was submitted
  - `ASSIGNMENT_CONFIRMED` — A service assignment was confirmed by a leader
  - `PLAN_FINALIZED` — The district plan was finalized/released
- API endpoints for CRUD on event mail hooks per district
- Admin UI for hook configuration (enable/disable, edit template, set recipient role)
- No new external dependencies — builds on MailService from `configurable-email-reminders`

## Capabilities

### New Capabilities
- `event-mail-hooks`: Per-district configuration of event-to-email mappings. Defines event types, recipient role targeting, subject/body templates (with event-specific placeholders), and active/inactive state. Includes the hook evaluator that listens for domain events and dispatches matching notifications.

### Modified Capabilities
- *(none – this is purely additive; existing features emit events but their core behavior is unchanged)*

## Impact

- **Backend** — New domain model (`EventMailHook`), new event dispatcher service, new API router, Alembic migration, integration points in existing services (sync service, registration service, matrix service, planning service) to emit domain events
- **Frontend** — New admin UI section for configuring event mail hooks per district
- **Dependencies** — None beyond `configurable-email-reminders` (MailService). Requires that change to be implemented first.
