## 1. Domain and Data Model

- [x] 1.1 Add domain entities/value objects for congregation invitations, invitation targets, and overwrite requests
- [x] 1.2 Add SQLAlchemy models/migrations for invitation relations, linked event references, and overwrite decision status
- [x] 1.3 Add repository ports for invitation management and overwrite request lifecycle

## 2. Backend Application and API

- [x] 2.1 Implement application services to create invitations and generate linked events per invited district congregation
- [x] 2.2 Implement source-event update propagation that creates `PENDING_OVERWRITE` requests for linked target events
- [x] 2.3 Implement API endpoints to list open overwrite requests and submit `ACCEPTED`/`REJECTED` decisions
- [x] 2.4 Extend event read endpoints to expose invitation-source hint for invited congregations
- [x] 2.5 Implement validation for invitation target type (`DISTRICT_CONGREGATION` xor `EXTERNAL_NOTE`) in request schemas

## 3. Matrix Invitation Targets

- [x] 3.1 Extend matrix backend DTOs/endpoints to store and return invitation target per congregation
- [x] 3.2 Add matrix API support for internal district target selection via `target_congregation_id`
- [x] 3.3 Add matrix API support for external invitation target hints via `external_target_note`
- [x] 3.4 Add integration tests for matrix invitation target persistence and validation errors

## 4. Frontend UX for Invitations

- [x] 4.1 Update matrix UI to edit/display invitation targets (district congregation picker or external free-text)
- [x] 4.2 Update event list/detail views to display invitation source congregation for invited events
- [x] 4.3 Add overwrite confirmation UI flow for invited congregations (view diff, accept, reject)
- [x] 4.4 Add frontend tests for invitation target editing and overwrite decision flows

## 6. Matrix Stability (Regression Fix)

- [x] 6.1 Restore matrix rendering so assignment grid remains visible in invitation-enabled mode
- [x] 6.2 Keep existing leader assignment workflow unchanged while invitation target option stays available

## 7. Host-Only Leader Assignment for Invitations

- [x] 7.1 Ensure invitation matrix cells mirror assignment from host service event
- [x] 7.2 Disable assignment editing in invited congregation cells and keep editing in host congregation only

## 8. API Semantics Alignment

- [x] 8.1 Remove congregation-level matrix invitation target endpoint usage in frontend/backend matrix flow
- [x] 8.2 Use event-based invitation creation from matrix cell context and update docs/spec language accordingly

## 9. Invitation Dialog Lifecycle

- [x] 9.1 Show invitation presence directly in matrix cells (host count + invited source hint)
- [x] 9.2 Allow listing and deleting invitations from the same matrix dialog used for assignment maintenance
- [x] 9.3 Prevent duplicate invitations per service/target by upsert behavior and surface existing invitations for edits

## 5. Quality and Rollout

- [x] 5.1 Add backend unit/integration tests for invitation creation, linked event generation, and overwrite workflow
- [x] 5.2 Verify existing event filtering/matrix behavior remains backward compatible with new invitation fields
- [x] 5.3 Document API contract changes and migration notes for invitation-enabled planning
