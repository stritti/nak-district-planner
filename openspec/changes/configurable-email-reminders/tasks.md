## 1. Domain Model

- [x] 1.1 Implement `DistrictReminderConfig` entity with required scheduling, content and ownership fields
- [x] 1.2 Implement `MailDeliveryError` exception class
- [x] 1.3 Define `MailRecord` dataclass (to, subject, body, sent_at)

## 2. MailService Port & Adapters

- [x] 2.1 Define abstract `MailService` port in `app/domain/ports/mail.py`
- [x] 2.2 Implement standard-library `SmtpMailService` adapter
- [x] 2.3 Implement `LogMailService` adapter for local development
- [x] 2.4 Implement capturing `MockMailService` test adapter
- [x] 2.5 Apply `EMAIL_FOOTER` centrally with `FooterMailService`
- [x] 2.6 Select the transport based on `APP_ENV` at the composition root

## 3. Persistence Layer

- [x] 3.1 Create the Alembic migration for district configurations and an idempotent monthly delivery ledger, with tenant RLS
- [x] 3.2 Implement configuration and delivery ledger SQLAlchemy ORM models
- [x] 3.3 Implement scoped `SqlDistrictReminderConfigRepository`

## 4. Configuration & Environment

- [x] 4.1 Add SMTP configuration and production fail-fast guard
- [x] 4.2 Add `EMAIL_FOOTER` to the environment configuration

## 5. Scheduler

- [x] 5.1 Implement `check_due_reminders` as a separate Celery task using a reusable application service
- [x] 5.2 Clamp days beyond the end of short months, including leap years
- [x] 5.3 Run Celery beat hourly in Europe/Berlin to respect configurable local send times (see design decision)
- [x] 5.4 Render the four supported placeholders using an explicit allowlist
- [x] 5.5 Use committed, unique monthly recipient claims and preserve uncertain send status for operator review

## 6. API Layer

- [x] 6.1 Define Create, Update and Response schemas
- [x] 6.2 Implement scoped POST endpoint
- [x] 6.3 Implement scoped GET endpoint
- [x] 6.4 Implement scoped PUT endpoint
- [x] 6.5 Implement soft-delete DELETE endpoint
- [x] 6.6 Enforce district-admin or superadmin authorization and database RLS

## 7. Frontend

- [x] 7.1 Add typed CRUD API client methods
- [x] 7.2 Add Pinia configuration state management
- [x] 7.3 Provide district-selected administration view at `/admin/reminders` and reusable reminder settings panel
- [x] 7.4 Implement configurable day, time, subject, body and role form
- [x] 7.5 Implement reminder list, edit and enable/disable actions

## 8. Tests and Verification

- [x] 8.1 Unit-test domain validation and due dates
- [x] 8.2 Unit-test SMTP, Log and Mock transport adapters
- [x] 8.3 Unit-test rendering and automatic footer composition
- [x] 8.4 Test short months, leap years and the scheduled-time boundary
- [x] 8.5 Unit-test scheduler dispatch, duplicate claims, absent recipients and per-recipient SMTP failures
- [x] 8.6 Unit-test API CRUD and district authorization; unit-test frontend API and store success/error paths
- [ ] 8.7 Add a database-backed integration test covering the full recipient-resolution, claim and send flow
- [ ] 8.8 Confirm the final commit's backend coverage, frontend tests, E2E, migrations, lint and security CI checks
