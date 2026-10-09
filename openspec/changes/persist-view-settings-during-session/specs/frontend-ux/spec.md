## ADDED Requirements

### Requirement: Session persistence of filters and sorting

The frontend SHALL retain the last selected filter values, sort field, sort direction and existing sorting options for each view during the same browser-tab session. This requirement SHALL apply to the planning matrix, the event list and other views that provide filters or sorting.

When the user leaves and reopens a view, navigates back or forward, or reloads the same tab, the view SHALL restore its valid session settings. The displayed controls and the requested or displayed results SHALL reflect the same restored state.

#### Scenario: Return to the matrix

- **WHEN** the user selects a congregation text filter and enables group sorting in the matrix, opens another view and returns during the same session
- **THEN** the matrix restores both settings and displays the matching congregations in the selected order

#### Scenario: Return to the event list

- **WHEN** the user selects filters and a sort field and direction in the event list, opens another view and returns during the same session
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
