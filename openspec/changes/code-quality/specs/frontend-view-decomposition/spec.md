## ADDED Requirements

### Requirement: Large views delegate to focused sub-components
`EventListView.vue`, `CalendarIntegrationsView.vue`, `LeadersAdminView.vue` and `DistrictsAdminView.vue` SHALL delegate filter controls, list/table rendering and create/edit modals to dedicated components under `src/components/`, keeping the view responsible only for orchestration (store access, routing and wiring events).

#### Scenario: EventListView decomposed
- **WHEN** a developer opens `EventListView.vue`
- **THEN** filter rendering, the event table and the event form modal are implemented in separate components

#### Scenario: CalendarIntegrationsView decomposed
- **WHEN** a developer opens `CalendarIntegrationsView.vue`
- **THEN** each integration is rendered by a card component and the form modal is a separate component

### Requirement: Decomposition preserves behaviour
The decomposition SHALL NOT change routes, API calls, permissions or user-visible behaviour, and existing unit and E2E tests SHALL keep passing.

#### Scenario: Regression suite after refactoring
- **WHEN** the refactored views are tested
- **THEN** the existing frontend unit and Playwright tests pass unchanged
