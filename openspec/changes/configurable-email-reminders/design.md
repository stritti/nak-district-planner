## Context

The planning workflow in a district follows a monthly cycle: by the 10th, planners should start assigning leaders to service slots; by the 20th, the plan should be finalized and approved. Currently there is no system that proactively reminds participants of these milestones. Administrators must rely on manual communication (e-mail, chat, verbal).

The existing infrastructure includes:
- Celery beat scheduler (task every 5 min for sync, daily for holiday import, etc.)
- RBAC roles (PLANNER, ADMIN, etc.) available via the `User` and `Membership` model
- Per-district configuration pattern already established (e.g., `state_code`, calendar integrations)

There is currently **no mail delivery infrastructure** in the system — no SMTP configuration, no mail templates, no send capability. This must be built from scratch.

## Goals / Non-Goals

**Goals:**
- Provide a configurable `DistrictReminderConfig` entity per district (day-of-month, time-of-day, subject, body, recipient role)
- Build an abstract `MailService` port with SMTP adapter for production and log/mock adapter for development
- Add a daily Celery beat task that evaluates reminder configurations and dispatches emails
- Add REST API endpoints for CRUD operations on reminder configurations
- Add a district admin UI for reminder configuration
- Support a system-wide email footer that is appended to all messages automatically

**Non-Goals:**
- Event-driven hooks (e.g., "LÜCKE detected → send mail") — will be proposed separately
- Per-user reminder preferences — all targeting is role-based
- Multi-language email templates — initial release in German only
- Email delivery tracking (bounce handling, open tracking) — basic send-and-forget
- Scheduling beyond monthly intervals (weekly, daily, one-off) — future extension

## Decisions

### 1. MailService Port — Abstract interface with pluggable adapters

```mermaid
┌─────────────────────────────────────────────────────┐
│                  MailService (ABC)                    │
│  + send(to: list[str], subject: str, body: str)      │
└─────────────────────┬───────────────────────────────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │  SMTP    │ │  Log     │ │  Mock    │
   │ Adapter  │ │  Adapter │ │  Adapter │
   ├──────────┤ ├──────────┤ ├──────────┤
   │Real mail │ │Log to    │ │Capture to│
   │via SMTP  │ │logger    │ │list for  │
   │server    │ │(dev)     │ │tests     │
   └──────────┘ └──────────┘ └──────────┘
```

**Decision:** Use Python standard library `smtplib` for the SMTP adapter (no external dependency). Use `aiosmtplib` only if async sending becomes necessary (Celery runs synchronously, so sync `smtplib` is sufficient). The Log adapter writes to `logger.info()` for development. The Mock adapter stores sent emails in an in-memory list for test assertions.

**Alternative considered:** External mail API (SendGrid, Mailjet) — rejected because SMTP is simpler, self-hostable, and avoids another API dependency for an MVP. Can be added later as another adapter.

### 2. Domain Model — DistrictReminderConfig

```text
DistrictReminderConfig
──────────────────────
  id: UUID
  district_id: UUID (FK → district)
  day_of_month: int (1-31)
  time_of_day: time (HH:MM, e.g. 10:00)
  subject_template: str (with placeholders)
  body_template: str (with placeholders)
  recipient_role: str (e.g. "PLANNER")
  is_active: bool
  created_at: datetime
  updated_at: datetime
```

**Decision:** Keep the model flat and per-district. Placeholders in templates: `{district_name}`, `{month}`, `{year}`, `{day}`. The system footer is not stored per-reminder but configured globally via settings (environment variable `EMAIL_FOOTER`).

**Alternative considered:** One global config with district overrides — rejected because each district has its own planning rhythm. Simpler to keep per-district from the start.

### 3. Recipient Resolution

Recipients are resolved at send-time by querying all users who have a `Membership` in the target district with the matching role (e.g., `PLANNER`). The `User.email` field is used as the recipient address.

**Decision:** Resolve at send-time, not config-creation-time, so new users with the correct role are automatically included.

### 4. Scheduling — Daily Celery Beat Task

A single daily task `check_due_reminders` runs at 01:00 Europe/Berlin. It queries all active `DistrictReminderConfig` records where `day_of_month == today.day` and `time_of_day <= current_time`. For each match, it resolves recipients and sends the mail.

```mermaid
01:00 daily ──▶ check_due_reminders()
                    │
                    ▼
              ┌────────────────┐
              │ Query all       │
              │ active configs  │
              │ where           │
              │ day == today    │
              └────────┬───────┘
                       │
              ┌────────▼────────┐
              │ For each match: │
              │ 1. Resolve role │
              │    → user emails│
              │ 2. Render       │
              │    template     │
              │ 3. MailService  │
              │    .send()      │
              └─────────────────┘
```

**Decision:** One task per day, not one task per reminder config. This keeps the beat schedule simple and allows batch processing. The cut-off at `time_of_day <= current_time` ensures reminders scheduled for e.g. 14:00 are not sent before that time even if the task runs early.

### 5. Email Templates

Templates are stored as plain strings (subject + body) in the `DistrictReminderConfig`. They support simple placeholder substitution (`{district_name}`, `{month}`, `{year}`, `{day}`). No HTML templating engine — plain text initially.

The system footer is appended to every outgoing mail body as a final paragraph:
```text
───
<footer_text>
```

**Reason:** Keeps implementation simple and avoids introducing a template engine dependency. If HTML emails are needed later, a richer template format can be added.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| **SMTP credentials in env** — credentials stored in environment variable, single point of failure | Follow existing pattern (`SECRET_KEY`, `OIDC_CLIENT_SECRET`). Already standard practice in this project. |
| **Day-of-month overflow** — reminder configured for 31st but month has only 28/30 days | Clamp to last day of month (e.g., config for 31st in February → send on 28th/29th). |
| **No email delivery confirmation** — network issues cause silent mail loss | Log send attempts and failures. Future: add delivery tracking to mail adapter. |
| **Template injection** — admin could inject malicious content via subject/body | Sanitize on output. Placeholder substitution only — no arbitrary rendering. |
| **Spam from misconfiguration** — high-frequency reminders could annoy users | Reminder is max 1× per day per config. `is_active` flag for quick disable. |

## Open Questions

- Should the system footer be a plain-text setting or point to an HTML template file? → Plain text setting (`EMAIL_FOOTER` env var) for MVP.
- Should reminder configs be deletable or only deactivatable? → Soft-delete via `is_active=false`; keep history.
- Should there be a per-district send-test endpoint to verify SMTP config? → Useful but deferred to post-MVP.
