## Why

The architectural review of #486, #487, #483, #484, #485, #491, #444 and #489 found a generally viable modular monolith, but cross-PR integration is not proved by individually green CI workflows. Release 1.0 needs explicit governance of migrations, calendar sync, access/publication boundaries and the OpenSpec baseline.

This change records architectural decisions and independently verifiable release gates. It does not assert that already addressed review comments are still bugs.

## What Changes

- Define the release integration gate on the actual combined merge candidate, not only individual PR heads.
- Specify migration graph and PostgreSQL upgrade verification, including the sibling Alembic heads introduced independently by #484 and #485.
- Require consistent calendar state transitions, authenticated tenant access, public/private export policies and stable generator identity across the combined implementation.
- Define OpenSpec baseline/active-change reconciliation and dependency direction as architectural governance.
- Separate mandatory 1.0 verification from post-1.0 structural refactoring.

## Architecture decisions

1. Retain a modular monolith (FastAPI, Celery/Beat, PostgreSQL, frontend). Do not create microservices merely to address code dependencies.
2. Domain owns deterministic planning invariants and visibility; application coordinates use cases and transactions; infrastructure owns HTTP, persistence, locks and delivery. RLS provides defence in depth, not a substitute for authorization and publication policy.
3. A calendar provider adapter normalizes untrusted input; synchronization policy decides outcomes; persistence records authoritative state transitions. Refactoring this boundary is follow-up work, not a prerequisite when current behavior is covered and safe.
4. The RC-2 legacy adapter-import allowlist in #444 is a temporary debt inventory. No new application-to-adapter dependencies; remove existing exemptions incrementally.
5. Public calendar feeds, internal feeds and personal leader feeds are distinct publication surfaces. Never infer public visibility solely from congregation applicability.
6. A stable generated-slot key identifies an occurrence independently of mutable display time.

## Scope

Release-critical: integration verification and corrections necessary to meet the existing business/security contracts, migration and OpenSpec coherence, tests of failure modes and concurrency.

Post-1.0: extract pure synchronization decisions and gradually remove allowlisted architecture debt with ports and injected infrastructure.

## Dependencies

- #486 before #487 (overlapping calendar changes).
- #484 before #485, then restack/linearize migration dependencies as appropriate.
- #444 before #489; reconcile #491's active generation spec with #489's archived baseline after integration.
- #483 touches calendar paths also changed by #486/#487; test the integrated result.

## Risks and non-goals

This proposal is not proof of a vulnerability in the current heads, does not reopen fixed Codex findings and does not promise a local test run. No wholesale domain rewrite, new distributed service, weakened security/coverage gate or unreviewed data migration.
