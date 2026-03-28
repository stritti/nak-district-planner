## Why

The system currently lacks a formally specified roles and permissions model. As governance, sync authority, notifications, and district-wide planning grow in complexity, explicit role-based access control (RBAC) is required to ensure security, clarity of responsibility, and predictable behavior.

## What Changes

- Introduce a global RBAC model with district and congregation scope.
- Define canonical system roles (e.g., DISTRICT_ADMIN, CONGREGATION_ADMIN, PLANNER, VIEWER).
- Specify permission boundaries for all major capabilities (planning, sync, ingestion, export, notifications).
- Define how roles are represented in authentication tokens (e.g., JWT claims).
- Establish authorization enforcement rules at application service level.

## Capabilities

### New Capabilities
- `rbac-model`: Role-based access control with scoped permissions and enforcement rules.

### Modified Capabilities
- `planning-model`: Add role-based constraints for creating, modifying, and deleting PlanningSeries and PlanningSlots.
- `hybrid-calendar-sync`: Restrict creation and modification of CalendarIntegration and sync configuration to authorized roles.
- `in-app-notifications`: Define which roles can view and act on governance notifications.

## Impact

- Backend domain model (Role, Membership, Scope definitions).
- Authentication layer (JWT claims or session model).
- Application services must enforce authorization checks.
- All API endpoints require role validation.
