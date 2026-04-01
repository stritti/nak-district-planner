## Context

The system includes planning governance, bidirectional calendar synchronization, token-based exports, and user-scoped authorization. Without explicit non-functional requirements, system behavior under load, failure, or misuse is undefined.

## Goals / Non-Goals

**Goals:**
- Define measurable performance targets.
- Define explicit security constraints.
- Define mandatory audit logging events.
- Define operational monitoring and retry policies.

**Non-Goals:**
- Implementation of specific monitoring vendors.
- Advanced distributed tracing architecture.

## Decisions

### 1. Performance Baseline
- Matrix API latency SHALL be ≤ 500ms for typical district scope (≤ 50 congregations, 3 months view).
- Sync job SHALL complete within configurable timeout (default 5 minutes per integration).

### 2. Security Baseline
- All credentials SHALL be encrypted at rest.
- Export tokens SHALL be cryptographically secure and at least 128-bit entropy.
- Rate limiting SHALL apply to public export endpoints.

### 3. Audit Logging
Audit log entries SHALL be created for:
- PlanningSlot creation/modification/deletion
- ServiceAssignment changes
- CalendarIntegration creation/modification/deletion
- Token creation/revocation

### 4. Operational Requirements
- Sync failures SHALL trigger structured logs.
- Repeated failures SHALL emit alert events.
- Retry with exponential backoff SHALL be applied for transient errors.

## Risks / Trade-offs

[Over-specification] → Keep baseline measurable but minimal.
[Operational Complexity] → Phase implementation with feature flags.

## Migration Plan

1. Introduce audit_log table.
2. Introduce rate limiting middleware.
3. Add structured logging to sync jobs.
4. Validate performance targets in staging.

Rollback: Disable enforcement checks while retaining logging.
