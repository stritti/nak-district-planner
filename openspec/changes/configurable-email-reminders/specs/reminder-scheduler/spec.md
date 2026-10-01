## ADDED Requirements

### Requirement: Hourly scheduler SHALL evaluate every active reminder configuration
The system SHALL invoke a Celery beat task hourly in Europe/Berlin. It SHALL evaluate active configurations for their configured day of the month and local time, with up to one hour scheduling granularity.

#### Scenario: Due reminder dispatched
- **WHEN** the hourly scheduler runs after an active reminder's configured local `time_of_day` on its scheduled local date
- **THEN** the system SHALL resolve recipients by role, render the email template, and send mail through `MailService`

#### Scenario: Reminder is not yet due
- **WHEN** the scheduler runs before the configured local time or on a different local date
- **THEN** it SHALL not dispatch that reminder

#### Scenario: No matching configuration
- **WHEN** the scheduler runs and no active reminder is due
- **THEN** it SHALL finish without sending any emails and log the summary

### Requirement: Recipient resolution SHALL use current district membership
The system SHALL resolve recipient addresses at dispatch time by joining users to memberships where `scope_type=DISTRICT`, `scope_id` equals the reminder's district and the membership role matches the configured `recipient_role` exactly. It SHALL exclude missing and duplicate email addresses. The existing membership schema does not define an `is_active` field, so role membership itself defines eligibility.

#### Scenario: Recipients resolved by role
- **WHEN** the scheduler resolves a reminder with `recipient_role=PLANNER`
- **THEN** the system SHALL select only users with a `PLANNER` membership in the exact district

#### Scenario: No recipients found
- **WHEN** no user has a matching membership or valid stored address
- **THEN** the system SHALL log a warning and skip dispatching that reminder

#### Scenario: Cross-district users excluded
- **WHEN** a user has the correct role but only in another district
- **THEN** they SHALL NOT receive the reminder

### Requirement: Template SHALL be rendered with a placeholder allowlist
The system SHALL replace `{district_name}`, `{month}`, `{year}`, and `{day}` in both subject and body. It SHALL NOT execute arbitrary template expressions.

#### Scenario: Placeholder values
- **WHEN** the scheduler renders a template for district "Bezirk Mitte" on March 15, 2026
- **THEN** `{district_name}` SHALL be "Bezirk Mitte", `{month}` SHALL be "März", `{year}` SHALL be "2026" and `{day}` SHALL be "15"

#### Scenario: Unknown placeholder
- **WHEN** a configured template contains an unsupported placeholder
- **THEN** the system SHALL preserve that literal text without evaluation

### Requirement: Month overflow SHALL be clamped
The scheduled local day SHALL be the configured day or the month's final calendar day, whichever is earlier.

#### Scenario: Non-leap-year February
- **WHEN** a reminder is configured for the 31st and the current month is February 2026
- **THEN** its scheduled date SHALL be February 28

#### Scenario: Leap-year February
- **WHEN** a reminder is configured for the 31st and the current month is February 2028
- **THEN** its scheduled date SHALL be February 29

### Requirement: Monthly dispatch SHALL be idempotent per recipient
The system SHALL persist a unique claim for each reminder ID, calendar month and recipient before invoking SMTP. Concurrent scheduler executions SHALL NOT dispatch a claimed reminder to the same address again that month.

#### Scenario: Scheduler checks same reminder twice
- **WHEN** a committed claim already exists for the recipient and month
- **THEN** the next check SHALL skip that dispatch

#### Scenario: SMTP fails after the claim
- **WHEN** SMTP delivery reports failure or a worker exits with uncertain delivery state
- **THEN** the claim SHALL remain unsent for explicit operator reconciliation; the scheduler SHALL NOT blindly retry and risk duplicate mail

#### Scenario: One recipient fails
- **WHEN** delivery fails for one recipient but others remain
- **THEN** the task SHALL log the failure and continue dispatching to the remaining recipients

### Requirement: Scheduler SHALL log outcomes
The system SHALL log a summary with evaluated, sent, skipped and failed counts after each run.
