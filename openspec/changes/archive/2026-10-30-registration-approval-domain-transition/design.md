## Context
Approval currently uses a private router helper to save a Leader and update all mutable registration state. Repository operations, HTTP authorization and external webhook provisioning remain in the same request transaction.

## Decision
The entity owns its approval state transition and validates the pending-state invariant. The helper still persists Leader and invokes entity.approve, so the existing rollback boundary and transactional event publication remain unchanged. Callers provide role, scope and actor; the entity provides UTC time unless one is passed for deterministic tests.

## Follow-up
The broader extraction into application services, repository ports and provisioning orchestration remains part of #714. Avoid performing it as one unsafe refactor immediately before a release.
