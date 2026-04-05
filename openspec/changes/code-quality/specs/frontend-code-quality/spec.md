## ADDED Requirements

### Requirement: Centralized HTTP client
The frontend SHALL use a single HTTP client instance for all API calls.

#### Scenario: API call with auth token
- **WHEN** any API call is made to a protected endpoint
- **THEN** the authentication header SHALL be injected automatically by the central HTTP client

#### Scenario: API call fails with 401
- **WHEN** an API response returns HTTP 401
- **THEN** the central HTTP client SHALL trigger a logout flow automatically

### Requirement: OAuth stub UI feedback
The system SHALL inform users that Google and Microsoft calendar integrations are not yet available.

#### Scenario: User selects Google or Microsoft integration type
- **WHEN** the user selects "Google" or "Microsoft" as the calendar integration type
- **THEN** the form SHALL be disabled and display a "Coming soon" badge

### Requirement: View component decomposition
Large view components SHALL be decomposed into focused sub-components.

#### Scenario: EventListView decomposed
- **WHEN** a developer opens `EventListView.vue`
- **THEN** the file SHALL delegate filter rendering to `EventFilters.vue`,
  table rendering to `EventTable.vue`, and modal logic to `EventFormModal.vue`

#### Scenario: CalendarIntegrationsView decomposed
- **WHEN** a developer opens `CalendarIntegrationsView.vue`
- **THEN** each integration SHALL be rendered by `IntegrationCard.vue`
  and the form modal by `IntegrationFormModal.vue`
