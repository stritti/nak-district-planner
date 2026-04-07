## ADDED Requirements

### Requirement: Global user feedback via toasts
The system SHALL display transient toast notifications for all user-triggered API actions.

#### Scenario: Successful action
- **WHEN** an API action completes successfully
- **THEN** the system SHALL display a success toast with a descriptive message for at least 3 seconds

#### Scenario: Failed action
- **WHEN** an API action fails
- **THEN** the system SHALL display an error toast with a human-readable message

#### Scenario: Toast queue overflow
- **WHEN** more than 3 toasts are queued simultaneously
- **THEN** the oldest toast SHALL be replaced by the newest

### Requirement: Calendar integration sync status
The system SHALL expose the last sync timestamp and result for each calendar integration.

#### Scenario: Sync status display
- **WHEN** the user views the calendar integrations list
- **THEN** each integration SHALL show `last_synced_at` and a color-coded status badge
  (green: recently synced, yellow: stale, red: last sync had errors)

#### Scenario: Sync result tooltip
- **WHEN** the user hovers over the sync status badge
- **THEN** a tooltip SHALL show the counts of created, updated, and cancelled events

### Requirement: Confirmation dialogs for destructive actions
The system SHALL require explicit user confirmation before executing any destructive action.

#### Scenario: Delete action confirmed
- **WHEN** a user initiates a delete, reject, or cancel action
- **THEN** a modal dialog SHALL appear describing the action and requiring confirmation before proceeding

#### Scenario: Confirmation declined
- **WHEN** the user clicks "Cancel" in the confirmation dialog
- **THEN** the action SHALL NOT be executed and the UI SHALL remain unchanged

### Requirement: Copy-to-clipboard for export tokens
The system SHALL provide a one-click copy mechanism for export token URLs.

#### Scenario: Copy export URL
- **WHEN** the user clicks the copy button next to an export URL
- **THEN** the URL SHALL be copied to the clipboard and a brief "Copied!" badge SHALL appear

### Requirement: Empty state components
The system SHALL display meaningful empty states when lists contain no items.

#### Scenario: Empty list
- **WHEN** a resource list (events, integrations, leaders) contains no items
- **THEN** the view SHALL display an explanatory text and a call-to-action button
