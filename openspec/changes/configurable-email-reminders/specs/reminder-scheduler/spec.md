## ADDED Requirements

### Requirement: Daily scheduler task SHALL check all active configurations
The system SHALL run a Celery beat task daily that evaluates all active reminder configurations and dispatches due reminders.

#### Scenario: Due reminder dispatched
- **WHEN** the daily scheduler runs and an active reminder configuration matches today's day_of_month and the current time is at or past the configured time_of_day
- **THEN** the system SHALL resolve recipients by role, render the email template, and send the email via MailService

#### Scenario: No matching configuration
- **WHEN** the daily scheduler runs and no active reminder configuration matches today's day_of_month
- **THEN** the system SHALL log that no reminders were due and complete without sending any emails

### Requirement: Recipient resolution SHALL use RBAC membership
The system SHALL resolve recipients by querying users with a Membership in the target district that has the configured recipient_role.

#### Scenario: Recipients resolved by role
- **WHEN** the scheduler resolves recipients for a reminder with recipient_role="PLANNER"
- **THEN** the system SHALL find all users with a Membership in the district where role_name="PLANNER" and is_active=true

#### Scenario: No recipients found
- **WHEN** the scheduler resolves recipients but no users have a matching role in the district
- **THEN** the system SHALL log a warning and skip sending

### Requirement: Template SHALL be rendered per reminder
The system SHALL render the subject_template and body_template with correct placeholder values before sending.

#### Scenario: Placeholder values
- **WHEN** the scheduler renders a template for a reminder in district "Bezirk Mitte" on March 15, 2026
- **THEN** `{district_name}` SHALL be replaced with "Bezirk Mitte", `{month}` with "März", `{year}` with "2026", `{day}` with "15"

### Requirement: Day-of-month overflow SHALL be clamped
The system SHALL clamp day_of_month values that exceed the number of days in the current month.

#### Scenario: 31st configured in February
- **WHEN** a reminder is configured for day_of_month=31 and the current month is February (28 days)
- **THEN** the reminder SHALL fire on the last day of February (28th)

### Requirement: Scheduler SHALL log results
The system SHALL log the outcome of each scheduler run for auditability.

#### Scenario: Summary log
- **WHEN** the daily scheduler completes
- **THEN** the system SHALL log a summary with the number of reminders evaluated, sent, and skipped
