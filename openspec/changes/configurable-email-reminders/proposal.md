## Why

District planners currently have no proactive notification system for the monthly planning workflow. Reminders about planning deadlines, approval cutoffs, and other recurring process steps must be communicated manually or are missed entirely. As the system grows to support multi-district planning with increasing numbers of leaders, a configurable, automated reminder system becomes essential for reliable workflow execution.

This change introduces a district-level configurable email reminder engine that supports the monthly planning cycle (remind planners to start planning on the 10th, remind them about approval on the 20th, etc.) and is extensible to future event-driven hooks.

## What Changes

- New domain entity `DistrictReminderConfig` for per-district reminder configuration
- New abstract `MailService` port with SMTP adapter for production and a mock/log adapter for development
- New Celery beat task that runs daily, evaluates scheduled reminders, and dispatches emails
- New API endpoints for CRUD operations on reminder configurations per district
- New admin UI for district-level reminder configuration
- Configurable email templates (subject + body) per reminder with system footer
- Recipient targeting based on RBAC roles (PLANNER role in the district)
- Time-of-day support on reminders (not just day-of-month) to avoid 00:00 sends

## Capabilities

### New Capabilities
- `reminder-configuration`: Per-district CRUD management of scheduled email reminders including day-of-month, time-of-day, subject, message body, and recipient role targeting
- `mail-delivery`: Abstract mail delivery port with SMTP adapter for production and file/log mock adapter for development, including HTML-capable template rendering with system footer
- `reminder-scheduler`: Celery beat task that runs daily, evaluates all active reminder configurations across all districts, and dispatches reminder emails to eligible recipients based on their RBAC role in the district

### Modified Capabilities
- *(none – this is a net-new feature)*

## Impact

- **Backend** — New domain model (`DistrictReminderConfig`), new ports (`MailService`), new adapter (`SmtpMailService`, `LogMailService`), new Celery beat task, new API router, Alembic migration
- **Frontend** — New admin view for reminder configuration within district settings
- **Configuration** — New environment variables for SMTP connection (host, port, user, password, from-address)
- **Dependencies** — SMTP library (Python standard library `smtplib` sufficient, or `aiosmtplib` for async) for production; no new dependencies for development mock
