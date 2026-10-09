# frontend-ux Specification

## Purpose

Cross-cutting user-experience behaviour of the Vue SPA: feedback toasts, confirmation of destructive actions, empty states, sync status display, export URL copying and role-based contextual help.

## Requirements

### Requirement: User feedback and safe destructive actions
The SPA SHALL show success and error toasts for API actions, SHALL ask for confirmation in a dialog before delete, reject or cancel actions, and SHALL show explanatory empty states with a call to action for empty resource lists.

#### Scenario: User cancels a deletion
- **WHEN** the user clicks "Abbrechen" in a confirmation dialog
- **THEN** the action is not executed

### Requirement: Integration status and export URLs
The calendar integrations view SHALL show `last_synced_at` and a colour-coded status per integration; export token URLs SHALL be copyable to the clipboard with visual confirmation.

#### Scenario: Copy export URL
- **WHEN** the user clicks the copy button of an export URL
- **THEN** the URL is in the clipboard and a short confirmation appears

### Requirement: Role-based contextual help
Views with a help context SHALL show non-blocking help modules filtered by authentication status and role (anonymous users get registration guidance; viewers and planners get role-specific workflows; other roles' content is hidden). Users SHALL be able to hide individual modules and restore them; hidden state is a per-browser preference keyed by identity, help ID and context.

#### Scenario: Viewer sees planner help
- **WHEN** a viewer opens a view that has planner-only help modules
- **THEN** those modules are not shown

### Requirement: Session persistence of filters and sorting

The frontend SHALL retain the last selected filter values, sort field, sort direction and existing sorting options for each view during the same browser-tab session. This requirement SHALL apply to the planning matrix, the event list and other views that provide filters or sorting.

When the user leaves and reopens a view, navigates back or forward, or reloads the same tab, the view SHALL restore its valid session settings. The displayed controls and the requested or displayed results SHALL reflect the same restored state.

#### Scenario: Return to the matrix

- **WHEN** the user selects a congregation text filter and enables group sorting in the matrix, opens another view and returns during the same session
- **THEN** the matrix restores both settings and displays the matching congregations in the selected order

#### Scenario: Return to the event list

- **WHEN** the user selects filters and, where provided, a sort field and direction in the event list, opens another view and returns during the same session
- **THEN** the event list restores those settings and displays the correspondingly filtered and sorted events

#### Scenario: Browser navigation and reload

- **WHEN** the user returns to a configured view using browser back or forward navigation, or reloads that view in the same tab
- **THEN** the valid filter and sorting settings remain selected and are applied to its results

### Requirement: Independent view and context settings

Session settings SHALL be isolated by authenticated user, view and applicable district or congregation context. Changing one view's settings SHALL NOT overwrite another view's settings. Settings SHALL NOT grant access to data outside the user's current permissions.

#### Scenario: Independent matrix and event list

- **WHEN** the user configures the matrix and then changes the event list's filters or sorting
- **THEN** each view retains its own last selected settings during the session

#### Scenario: Switch district or congregation

- **WHEN** the user switches to a different district or congregation context
- **THEN** the view uses that context's retained settings or its defaults if none exist
- **AND** returning to the previous context restores its still-valid settings

### Requirement: Session reset and valid restoration

Explicitly clearing filters or changing sorting SHALL update the retained state. Logging out or changing authenticated identity SHALL clear the previous user's retained and active settings. A new independent browser-tab session SHALL start with default settings; persistence across sessions or synchronization between tabs is not required.

Values that are no longer valid or accessible SHALL fall back to valid defaults while other valid settings remain intact. Missing, unavailable or malformed session storage SHALL NOT prevent the view from loading with defaults.

#### Scenario: Explicit filter reset

- **WHEN** the user clears the filters and later reopens the view during the same session
- **THEN** the view retains the cleared filter state instead of restoring the earlier selection

#### Scenario: Logout or identity change

- **WHEN** the user logs out or the authenticated identity changes
- **THEN** previous retained and active filter and sorting settings are cleared
- **AND** the next user starts with default settings

#### Scenario: New session

- **WHEN** the user starts a new independent browser-tab session
- **THEN** views use their default filter and sorting settings

#### Scenario: Selected group is no longer available

- **WHEN** a retained filter refers to a group that was deleted or is no longer accessible
- **THEN** that filter falls back to a valid default
- **AND** other valid filters and sorting settings are preserved

#### Scenario: Session storage cannot be restored

- **WHEN** session storage is missing, unavailable or malformed
- **THEN** the view remains usable and loads with valid default settings
