## Context

District planners work on monthly milestones. Administrators need configurable
monthly reminders without manual email coordination. The existing backend
provides Celery beat, scoped memberships, PostgreSQL/SQLAlchemy and strict
row-level security (RLS). This change introduces transport-agnostic mail delivery
and tenant-specific reminder configuration.

## Goals

- Configurable monthly reminders per district: day (1-31), local time, subject,
  plain-text body, exact district membership role and active state.
- Pluggable synchronous `MailService`: SMTP in production, logging in development,
  capturing mock in tests.
- An automatically appended system-wide plain-text footer.
- District-admin REST CRUD and a reminder administration view.
- Role membership resolution when a reminder is due, not when created.
- Monthly idempotency under overlapping scheduler checks.

## Non-goals

- Event-triggered notification rules, end-user preference controls and weekly,
  daily or one-off schedules.
- HTML and multilingual email templates.
- SMTP delivery confirmation, bounce handling or automatic replay of uncertain
  delivery attempts. Claim status is retained for explicit operator review.

## Architectural decisions

### Transport boundary

`app.domain.ports.mail.MailService` owns the synchronous `send()` contract.
`SmtpMailService`, `LogMailService`, and `MockMailService` are independent
adapters. `FooterMailService` decorates the selected adapter at the composition
root; transport adapters never append the footer themselves. Standard-library
`smtplib` is sufficient for the synchronous Celery worker and avoids adding a
mail API dependency. SMTP messages are sent separately per recipient to avoid
revealing members' addresses to other members. Header newlines are rejected.
Production requires a configured SMTP host and sender address; optional SMTP
credentials must be supplied together.

### District configuration and recipient scope

Each district owns zero or more `DistrictReminderConfig` entries. CRUD requires
`DISTRICT_ADMIN` of that district or the application's existing superadmin
privilege. All repository reads and updates include the district ID. RLS policies
reinforce the API-level authorization. A soft-delete sets `is_active=false`.
Recipients are resolved when due: users whose membership has exactly the
configured role and `scope_type=DISTRICT`, `scope_id=district_id`; duplicate and
missing addresses are filtered.

Templates use only `{district_name}`, `{month}`, `{year}` and `{day}`. Unknown
placeholders are retained literally. Rendering does not execute arbitrary
expressions and starts with plain text only.

### Monthly scheduling

Celery beat invokes the single `check_due_reminders` task **hourly** with the
`Europe/Berlin` timezone. Each reminder is due on its configured local day once
the configured local `time_of_day` has passed. For a day beyond the length of
the month, the last local day is used, including February leap years.

A previously proposed daily 01:00 evaluation was inconsistent with arbitrary
per-config `time_of_day` (for example, a 14:00 reminder could never dispatch
on its scheduled day). Hourly evaluation is intentionally used instead: the
time is respected with up to 59 minutes of scheduler granularity. An exact-time
per-reminder scheduler is outside this MVP.

### Idempotency and failure semantics

`reminder_deliveries` has a unique constraint on `(reminder_id,
scheduled_month, recipient)`. A worker inserts and **commits** a claim before
sending mail. The database uniqueness constraint prevents duplicate dispatches
when hourly checks overlap. A successful send writes `sent_at`. If SMTP reports
failure, or a worker dies between sending and recording success, the claim
remains without `sent_at`: it is intentionally **not** retried automatically
because SMTP might already have accepted the mail. Operators must reconcile an
uncertain claim before re-dispatch. This is at-most-once dispatch, not
guaranteed delivery; exactly-once delivery is unavailable via plain SMTP.
Failures for an individual recipient do not abort dispatch for other recipients.

### Security and operations

The migration enables and forces RLS for reminder configurations and the
monthly delivery ledger. Configurations are available to the district admin,
superadmin and system worker. The delivery ledger is system-worker only.
Workers use the existing bounded system-worker tenant context. SMTP errors are
translated into `MailDeliveryError` without logging credentials. Startup fails
in production when SMTP essentials are missing rather than silently switching
to the development logging adapter. `EMAIL_FOOTER` is centrally configured.

## Risks and trade-offs

| Risk | Mitigation |
|------|------------|
| Month has fewer days than configured | Clamp to that month's final day. |
| Multiple workers evaluate concurrently | Unique persisted claim before SMTP side effect. |
| SMTP accepts mail before a worker crashes | Do not auto-retry uncertain claims; require explicit reconciliation. |
| Wrong district or role receives mail | Exact district membership and role match; application RBAC plus database RLS. |
| Configured send time falls between checks | Document hourly granularity. |
| Template/header injection | Allowlist placeholder renderer; reject header newlines. |

## Deferred follow-ups

A per-district test-send endpoint, operational dashboard for uncertain sends,
HTML templating, and exact-minute scheduling can be specified separately.
