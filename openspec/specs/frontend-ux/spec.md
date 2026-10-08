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
