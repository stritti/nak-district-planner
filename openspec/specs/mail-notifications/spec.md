# mail-notifications Specification

## Purpose

E-mail delivery for district communication: a framework-free mail port with SMTP, log and mock adapters, configurable monthly reminders, event-driven mail hooks on domain events, and the daily service-gap scan that feeds them.

## Requirements

### Requirement: Mail port and adapters
The domain SHALL define a `MailService` port with `send(to, subject, body)`. The composition root SHALL use the SMTP adapter in production (`SMTP_*`, `EMAIL_FROM_ADDRESS`), a mock adapter in tests and a log adapter otherwise, and SHALL append `EMAIL_FOOTER` after a `\n---\n` separator exactly once when configured. SMTP failures SHALL raise `MailDeliveryError`.

#### Scenario: No footer configured
- **WHEN** `EMAIL_FOOTER` is empty
- **THEN** the body is sent without separator or footer

### Requirement: SMTP credentials require verified TLS
The SMTP adapter SHALL NOT authenticate unless the connection was upgraded with STARTTLS using a certificate- and hostname-verifying context. Production startup SHALL be refused when `SMTP_USER`/`SMTP_PASSWORD` are set together with `SMTP_STARTTLS=false`. A relay without authentication MAY be used without STARTTLS only as an explicit operator choice.

#### Scenario: Credentials with TLS disabled
- **WHEN** `SMTP_USER` and `SMTP_PASSWORD` are configured and `SMTP_STARTTLS` is `false`
- **THEN** the production guard and the adapter constructor reject the configuration before any mail is sent

#### Scenario: STARTTLS unavailable or certificate invalid
- **WHEN** the server offers no STARTTLS or the certificate fails verification
- **THEN** delivery fails with `MailDeliveryError`
- **AND** the password is never transmitted

### Requirement: Reminder configuration
District admins SHALL manage reminder configurations under `/api/v1/districts/{id}/reminder-configs` (create, list incl. inactive, update, delete) with day of month, local time, `recipient_role` (an RBAC role), subject and body templates and `is_active`.

#### Scenario: Invalid recipient role
- **WHEN** a configuration names a role that does not exist
- **THEN** the API responds with 422

### Requirement: Reminder dispatch
The beat task `check_due_reminders` SHALL run hourly and dispatch due active reminders (day clamped to the month's last day) to users whose district membership role equals `recipient_role`, substituting only `{district_name}`, `{month}`, `{year}` and `{day}`. A unique delivery claim per reminder, month and recipient SHALL be persisted before sending; failed sends SHALL be logged and not retried automatically.

#### Scenario: Overlapping runs
- **WHEN** two scheduler runs evaluate the same due reminder
- **THEN** each recipient receives the mail at most once that month

#### Scenario: Unknown placeholder
- **WHEN** a template contains `{unknown_field}`
- **THEN** the literal text is kept and no expression is evaluated

#### Scenario: Run summary
- **WHEN** a scheduler run finishes
- **THEN** evaluated, sent, skipped and failed counts are logged

### Requirement: Event mail hooks
District admins SHALL configure mail hooks per event type (`SLOT_UNASSIGNED`, `EXTERNAL_EVENT_DETECTED`, `SYNC_ERROR`, `REGISTRATION_RECEIVED`, `ASSIGNMENT_CONFIRMED`, `PLAN_FINALIZED`) under `/api/v1/districts/{id}/event-hooks`; deletion SHALL deactivate the hook. Domain events SHALL be published after commit and dispatched by a Celery task to the district's active hooks with event-specific placeholders. Sending hook mails SHALL NOT emit further domain events.

#### Scenario: Assignment confirmed
- **WHEN** an assignment is newly confirmed and an active `ASSIGNMENT_CONFIRMED` hook exists
- **THEN** recipients with the hook's role receive the rendered mail

### Requirement: Service gap scan
The beat task `scan_slot_gaps` SHALL run daily at 06:15, report each newly opened service gap once as `SLOT_UNASSIGNED`, and forget closed gaps so that a reopened gap is reported again.

#### Scenario: Gap stays open
- **WHEN** a gap was already reported and is still open on the next scan
- **THEN** no further `SLOT_UNASSIGNED` event is emitted

### Requirement: STARTTLS must be verified against a real SMTP server
The SMTP adapter SHALL be integration-tested with a local TLS-capable SMTP test server and SHALL NOT authenticate until STARTTLS has succeeded with a certificate- and hostname-validating SSL context.

#### Scenario: Valid STARTTLS
- **WHEN** a trusted local SMTP server advertises STARTTLS with a matching hostname
- **THEN** the client negotiates TLS before sending authentication credentials
- **AND** a test message is accepted by the local server only after the expected handshake

#### Scenario: No STARTTLS advertised
- **WHEN** an authenticated SMTP connection encounters a server without STARTTLS
- **THEN** the send attempt fails and no AUTH command is sent

#### Scenario: Invalid certificate or hostname
- **WHEN** the server's certificate is untrusted or its hostname does not match
- **THEN** the send attempt fails without sending AUTH or message data

#### Scenario: STARTTLS handshake failure
- **WHEN** an advertised STARTTLS handshake fails
- **THEN** no authentication or message content is sent

### Requirement: Staging relay smoke validation
An operator SHALL verify the configured staging/production relay hostname and STARTTLS certificate before enabling credentialed SMTP delivery. This operation SHALL not log passwords or send external mail in handshake-only mode.

#### Scenario: Predeployment verification
- **WHEN** the operator runs the relay smoke check
- **THEN** TLS verification and the recorded result are available in the production runbook
