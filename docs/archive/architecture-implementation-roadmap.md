# Architecture implementation sequencing

This is **architectural guidance**, not the product release backlog. The original PlanningSlot, RBAC, sync-metadata, hardened-sync and non-functional-baseline phase plan was historical preparation for v1.0.0. See the [current roadmap](../../docs/roadmap.md), [OpenSpec baseline](../specs/) and [active changes](../changes/).

## Cross-cutting changes: recommended sequence

1. Model domain invariants and ownership, including PlanningSlot and EventInstance.
2. Define RBAC and tenant-isolation boundaries before public APIs.
3. Evolve sync and external interfaces while preserving idempotency and visibility.
4. Add UI, migrations, negative tests, observability and rollback guidance.
5. Synchronize the baseline and archive the delivered change.

Independent fixes need not wait for unrelated phases. The architecture reference is [overview.md](overview.md). The original time estimates and flags remain in [Git history](https://github.com/stritti/nak-district-planner/blob/2b20473b3791370495a31384b58ce1b254371ab1/openspec/architecture/implementation-roadmap.md).
