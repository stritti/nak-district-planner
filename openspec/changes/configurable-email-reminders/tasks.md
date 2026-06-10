## 1. Domain Model

- [ ] 1.1 Implement `DistrictReminderConfig` entity in `app/domain/models/` with fields: id, district_id, day_of_month, time_of_day, subject_template, body_template, recipient_role, is_active, created_at, updated_at
- [ ] 1.2 Implement `MailDeliveryError` exception class
- [ ] 1.3 Define `MailRecord` dataclass (to, subject, body, sent_at)

## 2. MailService Port & Adapters

- [ ] 2.1 Define abstract `MailService` port in `app/domain/ports/mail.py` with `send(to: list[str], subject: str, body: str)` method
- [ ] 2.2 Implement `SmtpMailService` adapter in `app/adapters/mail/smtp.py` using standard library `smtplib`
- [ ] 2.3 Implement `LogMailService` adapter in `app/adapters/mail/log.py` that logs email content at INFO level
- [ ] 2.4 Implement `MockMailService` adapter in `app/adapters/mail/mock.py` that captures emails in memory for testing
- [ ] 2.5 Implement footer appending utility that adds `EMAIL_FOOTER` (separated by `\n---\n`) to all outgoing bodies
- [ ] 2.6 Add `MailService` dependency injection factory in `app/adapters/mail/__init__.py` that selects adapter based on `APP_ENV`

## 3. Persistence Layer

- [ ] 3.1 Create Alembic migration for `district_reminder_config` table
- [ ] 3.2 Implement SQLAlchemy ORM model for `DistrictReminderConfigORM`
- [ ] 3.3 Implement `SqlDistrictReminderConfigRepository` with CRUD methods

## 4. Configuration & Environment

- [ ] 4.1 Add SMTP settings to `app/config.py`: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM_ADDRESS
- [ ] 4.2 Add `EMAIL_FOOTER` setting to `app/config.py`

## 5. Scheduler

- [ ] 5.1 Implement `check_due_reminders` Celery task in `app/application/tasks.py` that queries all active configs, resolves recipients by RBAC role, renders templates, and sends via MailService
- [ ] 5.2 Add day-of-month clamping logic (config day > month days → clamp to last day)
- [ ] 5.3 Add `check_due_reminders` to Celery beat schedule in `app/celery_app.py` (daily at 01:00 Europe/Berlin)
- [ ] 5.4 Implement placeholder substitution (`{district_name}`, `{month}`, `{year}`, `{day}`) in subject/body templates

## 6. API Layer

- [ ] 6.1 Create `DistrictReminderConfig` Pydantic schemas (Create, Update, Response)
- [ ] 6.2 Implement `POST /api/v1/districts/{district_id}/reminder-configs` endpoint
- [ ] 6.3 Implement `GET /api/v1/districts/{district_id}/reminder-configs` endpoint
- [ ] 6.4 Implement `PUT /api/v1/districts/{district_id}/reminder-configs/{config_id}` endpoint
- [ ] 6.5 Implement `DELETE /api/v1/districts/{district_id}/reminder-configs/{config_id}` endpoint (soft-delete via is_active=false)
- [ ] 6.6 Protect all endpoints with RBAC permission checks (district admin or global admin)

## 7. Frontend

- [ ] 7.1 Add API client methods for reminder config CRUD in `app/api/reminderConfigs.ts`
- [ ] 7.2 Add Pinia store for reminder configuration state
- [ ] 7.3 Add reminder configuration section to district settings view
- [ ] 7.4 Implement reminder config form (day, time, subject, body, role select)
- [ ] 7.5 Implement reminder config list with enable/disable toggle per config

## 8. Tests

- [ ] 8.1 Unit tests for `DistrictReminderConfig` domain model
- [ ] 8.2 Unit tests for all three MailService adapters (SMTP mocked, Log, Mock)
- [ ] 8.3 Unit tests for placeholder substitution and footer appending
- [ ] 8.4 Unit tests for day-of-month clamping logic
- [ ] 8.5 Unit tests for Celery scheduler task (with mocked MailService)
- [ ] 8.6 Unit tests for reminder config API endpoints
- [ ] 8.7 Integration tests for full reminder send flow
