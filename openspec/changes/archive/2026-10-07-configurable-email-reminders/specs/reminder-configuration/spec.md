## ADDED Requirements

### Requirement: District admin can create reminder configurations
The system SHALL allow a district admin to create email reminder configurations for their district.

#### Scenario: Successful creation
- **WHEN** a district admin submits a new reminder configuration with day_of_month (1-31), time_of_day (HH:MM), subject_template, body_template, and recipient_role
- **THEN** the system SHALL create a new DistrictReminderConfig record and return it with status 201

#### Scenario: Invalid day of month
- **WHEN** a district admin submits a reminder configuration with day_of_month outside 1-31
- **THEN** the system SHALL return a validation error with status 422

#### Scenario: Missing required fields
- **WHEN** a district admin submits a reminder configuration without required fields (subject_template, body_template, recipient_role)
- **THEN** the system SHALL return a validation error with status 422

### Requirement: District admin can list reminder configurations
The system SHALL allow a district admin to view all reminder configurations for their district.

#### Scenario: List all configurations
- **WHEN** a district admin requests the list of reminder configurations for their district
- **THEN** the system SHALL return all active and inactive configurations for that district

### Requirement: District admin can update a reminder configuration
The system SHALL allow a district admin to modify an existing reminder configuration.

#### Scenario: Successful update
- **WHEN** a district admin updates an existing reminder configuration's day_of_month, time_of_day, subject_template, body_template, or recipient_role
- **THEN** the system SHALL persist the changes and return the updated configuration

#### Scenario: Update non-existent configuration
- **WHEN** a district admin attempts to update a reminder configuration that does not exist
- **THEN** the system SHALL return status 404

### Requirement: District admin can deactivate a reminder configuration
The system SHALL allow soft-deletion of a reminder configuration via an is_active flag.

#### Scenario: Deactivate configuration
- **WHEN** a district admin sets is_active=false on a reminder configuration
- **THEN** the system SHALL mark the configuration as inactive and the daily scheduler SHALL skip it

#### Scenario: Reactivate configuration
- **WHEN** a district admin sets is_active=true on a previously deactivated configuration
- **THEN** the system SHALL resume processing of the configuration in the daily scheduler

### Requirement: Recipient role SHALL use RBAC role names
The recipient_role field SHALL reference valid RBAC role names (e.g., PLANNER, ADMIN).

#### Scenario: Invalid role rejected
- **WHEN** a district admin submits a reminder configuration with a recipient_role that does not match an existing RBAC role
- **THEN** the system SHALL return a validation error with status 422

### Requirement: Template placeholders SHALL be substituted
The system SHALL support placeholder substitution in subject_template and body_template.

#### Scenario: Placeholder substitution in body
- **WHEN** a reminder is sent and the body_template contains `{district_name}`, `{month}`, `{year}`, or `{day}`
- **THEN** the system SHALL replace each placeholder with the corresponding actual value before sending

#### Scenario: Unknown placeholder preserved
- **WHEN** a body_template contains a placeholder like `{unknown_field}` that has no mapping
- **THEN** the system SHALL preserve the literal text `{unknown_field}` unchanged
