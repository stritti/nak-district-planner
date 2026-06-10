## ADDED Requirements

### Requirement: EventMailHook domain model
The system SHALL define an `EventMailHook` entity with the following fields: `id` (UUID), `district_id` (UUID), `event_type` (str), `recipient_role` (str), `subject_template` (str), `body_template` (str), `is_active` (bool), `created_at` (datetime), `updated_at` (datetime).

#### Scenario: Create EventMailHook
- **WHEN** an admin creates a new event mail hook for a district
- **THEN** the system SHALL persist the hook with a unique UUID, current timestamps, and `is_active` defaulting to true

#### Scenario: Deactivate EventMailHook
- **WHEN** an admin deactivates an event mail hook
- **THEN** the system SHALL set `is_active` to false and update `updated_at`

### Requirement: Pre-defined event types
The system SHALL support the following event types for event mail hooks: `SLOT_UNASSIGNED`, `EXTERNAL_EVENT_DETECTED`, `SYNC_ERROR`, `REGISTRATION_RECEIVED`, `ASSIGNMENT_CONFIRMED`, `PLAN_FINALIZED`.

#### Scenario: Known event types accepted
- **WHEN** an admin creates an event mail hook with one of the known event types
- **THEN** the system SHALL accept and store the configuration

#### Scenario: Unknown event type rejected
- **WHEN** an admin creates an event mail hook with an unknown event type
- **THEN** the system SHALL reject the request with a 422 validation error

### Requirement: DomainEventBus
The system SHALL provide an in-process `DomainEventBus` that allows services to emit events and handlers to subscribe.

#### Scenario: Emit event
- **WHEN** a service emits a `DomainEvent` with an event type, district_id, and payload
- **THEN** the event bus SHALL deliver the event to all registered handlers for that event type

#### Scenario: Subscribe handler
- **WHEN** a handler subscribes to an event type on the event bus
- **THEN** the event bus SHALL invoke that handler for every future event of that type

### Requirement: DomainEvent contract
The system SHALL define a `DomainEvent` dataclass with fields: `event_type` (str), `district_id` (UUID), `payload` (dict), `occurred_at` (datetime).

#### Scenario: Event created with timestamp
- **WHEN** a `DomainEvent` is instantiated
- **THEN** the `occurred_at` field SHALL be set to the current UTC timestamp

### Requirement: HookEvaluator dispatches email for matching hooks
The system SHALL provide a `HookEvaluator` that subscribes to all event types on the `DomainEventBus`. For each received event, it SHALL query active `EventMailHook` records where `event_type` matches and `district_id` matches, then dispatch emails via the MailService.

#### Scenario: Event matches active hook
- **WHEN** a `DomainEvent` is emitted and an active `EventMailHook` exists for that event type and district
- **THEN** the HookEvaluator SHALL:
  - Resolve recipient email addresses via `Membership` for the configured role in the target district
  - Render the subject and body templates with event-placeholder substitution
  - Append the system footer to the body
  - Call `MailService.send()` with the recipients, rendered subject, and rendered body

#### Scenario: Event matches no hook
- **WHEN** a `DomainEvent` is emitted and no active `EventMailHook` exists for that event type and district
- **THEN** the HookEvaluator SHALL silently ignore the event

#### Scenario: Event matches inactive hook
- **WHEN** a `DomainEvent` is emitted and a matching hook exists but has `is_active=false`
- **THEN** the HookEvaluator SHALL silently ignore the event

#### Scenario: Event emitted from non-district context
- **WHEN** a `DomainEvent` is emitted with a `district_id` that does not match any district
- **THEN** the HookEvaluator SHALL silently ignore the event

### Requirement: Event-type specific placeholders
The system SHALL support event-type-specific placeholder substitution in email templates for event mail hooks.

#### Scenario: SLOT_UNASSIGNED placeholders
- **WHEN** a `SLOT_UNASSIGNED` event is dispatched
- **THEN** the renderer SHALL substitute `{district_name}`, `{congregation_name}`, `{date}`, `{event_title}` with values from the event payload

#### Scenario: EXTERNAL_EVENT_DETECTED placeholders
- **WHEN** an `EXTERNAL_EVENT_DETECTED` event is dispatched
- **THEN** the renderer SHALL substitute `{district_name}`, `{event_title}`, `{event_date}`, `{source}` with values from the event payload

#### Scenario: SYNC_ERROR placeholders
- **WHEN** a `SYNC_ERROR` event is dispatched
- **THEN** the renderer SHALL substitute `{district_name}`, `{integration_name}`, `{error_message}`, `{timestamp}` with values from the event payload

#### Scenario: REGISTRATION_RECEIVED placeholders
- **WHEN** a `REGISTRATION_RECEIVED` event is dispatched
- **THEN** the renderer SHALL substitute `{district_name}`, `{leader_name}`, `{leader_email}` with values from the event payload

#### Scenario: ASSIGNMENT_CONFIRMED placeholders
- **WHEN** an `ASSIGNMENT_CONFIRMED` event is dispatched
- **THEN** the renderer SHALL substitute `{district_name}`, `{leader_name}`, `{event_title}`, `{event_date}` with values from the event payload

#### Scenario: PLAN_FINALIZED placeholders
- **WHEN** a `PLAN_FINALIZED` event is dispatched
- **THEN** the renderer SHALL substitute `{district_name}`, `{month}`, `{year}` with values from the event payload

#### Scenario: Missing placeholder rendered as blank
- **WHEN** a template uses a placeholder that is not present in the event payload
- **THEN** the renderer SHALL replace it with an empty string (not raise an error)

### Requirement: Event emission points in existing services
The system SHALL emit domain events at specific points in existing service operations.

#### Scenario: LÜCKE detection emits SLOT_UNASSIGNED
- **WHEN** the sync or matrix service detects a planning slot of category `Gottesdienst` without a `ServiceAssignment`
- **THEN** the system SHALL emit a `SLOT_UNASSIGNED` event with the slot's congregation, date, and title

#### Scenario: ExternalEventCandidate creation emits EXTERNAL_EVENT_DETECTED
- **WHEN** an `ExternalEventCandidate` is created by the calendar sync
- **THEN** the system SHALL emit an `EXTERNAL_EVENT_DETECTED` event with the event title, date, and source

#### Scenario: Sync job failure emits SYNC_ERROR
- **WHEN** a calendar sync job fails with an exception
- **THEN** the system SHALL emit a `SYNC_ERROR` event with the integration name and error message

#### Scenario: Leader registration approval emits REGISTRATION_RECEIVED
- **WHEN** a leader registration is approved
- **THEN** the system SHALL emit a `REGISTRATION_RECEIVED` event with the leader's name and email

#### Scenario: Assignment confirmation emits ASSIGNMENT_CONFIRMED
- **WHEN** a `ServiceAssignment` status changes to `CONFIRMED`
- **THEN** the system SHALL emit an `ASSIGNMENT_CONFIRMED` event with the leader name, event title, and event date

#### Scenario: Plan finalization emits PLAN_FINALIZED
- **WHEN** a district plan is finalized (e.g., via API or admin action)
- **THEN** the system SHALL emit a `PLAN_FINALIZED` event with the district name, month, and year

### Requirement: HookEvaluator SHALL NOT emit events
The system SHALL ensure the HookEvaluator never triggers additional events when sending email notifications.

#### Scenario: No event emission during mail dispatch
- **WHEN** the HookEvaluator sends an email via `MailService.send()`
- **THEN** the system SHALL NOT emit any domain event as a side effect of that send operation

### Requirement: Event mail hook CRUD API
The system SHALL provide REST API endpoints for managing event mail hooks per district, protected by RBAC (district admin or global admin).

#### Scenario: List event hooks
- **WHEN** an admin sends `GET /api/v1/districts/{district_id}/event-hooks`
- **THEN** the system SHALL return all event mail hooks for that district, including inactive ones

#### Scenario: Create event hook
- **WHEN** an admin sends `POST /api/v1/districts/{district_id}/event-hooks` with valid event_type, recipient_role, subject_template, and body_template
- **THEN** the system SHALL create and return the new event mail hook

#### Scenario: Update event hook
- **WHEN** an admin sends `PUT /api/v1/districts/{district_id}/event-hooks/{hook_id}` with updated fields
- **THEN** the system SHALL update and return the modified event mail hook

#### Scenario: Delete event hook (soft)
- **WHEN** an admin sends `DELETE /api/v1/districts/{district_id}/event-hooks/{hook_id}`
- **THEN** the system SHALL set `is_active=false` and return 204 No Content

#### Scenario: Create with unknown event type
- **WHEN** an admin sends `POST /api/v1/districts/{district_id}/event-hooks` with an unknown event_type
- **THEN** the system SHALL return 422 Unprocessable Entity

#### Scenario: Unauthorized access
- **WHEN** a user without district admin or global admin role tries to access the event hook API
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Event mail hook admin UI
The system SHALL provide a district admin UI section for managing event mail hooks.

#### Scenario: View event hooks list
- **WHEN** an admin navigates to the district settings > Event Hooks section
- **THEN** the system SHALL display all event hooks for that district with event type, recipient role, status, and action buttons

#### Scenario: Toggle hook active state
- **WHEN** an admin toggles an event hook's active state
- **THEN** the system SHALL update the hook's `is_active` field and reflect the new state immediately

#### Scenario: Create event hook from UI
- **WHEN** an admin fills the creation form with event type, role, subject, body, and submits
- **THEN** the system SHALL create the event hook and display it in the list
