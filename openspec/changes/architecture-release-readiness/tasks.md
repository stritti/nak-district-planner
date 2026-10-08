## 1. Release 1.0: integrated gates

- [ ] 1.1 Record the exact release integration commit(s), merged PR revisions and dependency order (#486 → #487; #484 → #485; #444 → #489; reconcile #483 and #491 with overlapping changes).
- [ ] 1.2 Integrate #484 and #485 and verify a single Alembic head, database upgrade, model drift check and documented downgrade behavior. Include legacy assignments and holiday records.
- [ ] 1.3 Run PostgreSQL tenant/RLS and export integration tests as the restricted production role, including PUBLIC/INTERNAL event visibility, distributed district slots, leader names and existing legacy assignments.
- [ ] 1.4 Run combined calendar regression tests for ICS/CalDAV, RRULE/EXDATE/RECURRENCE-ID, incomplete snapshots, moved-out-of-window events, DST, data deletion and unsupported provider preflight. Confirm the SSRF guard's bounded DNS/connect/TLS/body behavior.
- [ ] 1.5 Run concurrency and idempotency tests for assignment uniqueness, advisory locks and generated service identity; include concurrent generators, moved/reassigned/cancelled slots and migration duplicates.
- [ ] 1.6 After #444 and #491 integration, reconcile #489's `openspec/specs/` baseline with pending active deltas and archived changes; run strict OpenSpec validation.
- [ ] 1.7 Verify the integrated frontend and backend tests, security scans, lints, E2E, build, dependency checks, backup/restore drill and coverage >80%; attach exact run links and coverage reports to the release PR.
- [ ] 1.8 Review unresolved threads against final code, close only verified or explicitly accepted decisions, and record any remaining release blockers.

## 2. Architecture governance for 1.0

- [ ] 2.1 Preserve #444's architecture dependency regression gate; reject new application-to-infrastructure imports outside the documented legacy inventory.
- [ ] 2.2 Document transactional and external-provider side-effect boundaries in the sync code and OpenSpec, including what an application rollback cannot undo.
- [ ] 2.3 Document the distinct policies for business applicability, tenant authorization and PUBLIC/INTERNAL/personal publication.

## 3. After 1.0 (not release blocking unless a concrete defect is found)

- [ ] 3.1 Extract provider-neutral pure synchronization decisions and state transitions behind domain/application interfaces while maintaining regression behavior.
- [ ] 3.2 Replace the highest-risk legacy application imports with ports and composition-root injection, removing exact entries from #444's allowlist as debt is repaid.
- [ ] 3.3 Add cross-module architecture tests ensuring all planned service mutations use invariant-preserving application entry points.
- [ ] 3.4 Revisit recurring calendar revision metadata and unsubscribed/previously assigned leader feed semantics based on observed compatibility, not speculative release blocking.
