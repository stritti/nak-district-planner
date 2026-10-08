## Context

The NAK District Planner includes multi-tenant structures (District, Congregation) and governance-sensitive workflows (planning, sync, ingestion, export). Without a formal RBAC model, authorization decisions would become ad hoc and inconsistent.

## Goals / Non-Goals

**Goals:**
- Define a canonical set of roles.
- Support district-scoped and congregation-scoped permissions.
- Ensure enforcement occurs in the application layer.
- Integrate roles into authentication tokens.

**Non-Goals:**
- Complex attribute-based access control (ABAC).
- Fine-grained per-field permissions.

## Decisions

### 1. Role Model
Roles are assigned via Membership:

```text
User
  └── Membership
        - role
        - scope_type (DISTRICT | CONGREGATION)
        - scope_id
```

Canonical roles:
- DISTRICT_ADMIN
- CONGREGATION_ADMIN
- PLANNER
- VIEWER

### 2. Enforcement Strategy
Authorization is enforced in application services, not routers.
Each use case checks required role before execution.

### 3. Token Integration
JWT contains:
- user_id
- list of memberships (role + scope)

## Risks / Trade-offs

[Over-restriction] → Start minimal and extend roles only when necessary.
[Token Size] → Keep membership claims concise; consider DB lookup if needed.

## Migration Plan

1. Introduce Role and Membership tables.
2. Assign default roles to existing users.
3. Add authorization guards to services.

Rollback: Feature-flag enforcement layer.
