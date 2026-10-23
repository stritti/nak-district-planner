# Domain approval transition – bounded refactor (#714)

## Design
Begin by separating authorization state mutation from the FastAPI adapter. Keep the existing SQLAlchemy transaction, RLS authorization and webhook/outbox orchestration unchanged. Defer larger service/port refactor to follow-up.

## Implementation
1. Add regression tests for correct metadata, rejecting resolved registrations and deterministic UTC timestamp.
2. Add domain method LeaderRegistration.approve.
3. Replace field-by-field mutations in router helper with domain call.
4. Add an OpenSpec requirement and verify unit + PostgreSQL tests in CI (>80% coverage).

## Review
Ensure previously nonpending registrations are not mutated. Avoid a new premature infrastructure abstraction or transaction boundary.
