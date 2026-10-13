# Dependent event changes implementation plan

Base: feat/inline-edit-matrix (matrix stacked PR).

- Date/time, congregation and related service-assignment changes require domain-level atomic validation.
- Capture original event revision and use If-Match under a transaction-scoped lock.
- Show impact on assignments before commit, require confirmation when existing domain workflow requires it.
- Revalidate responsible leaders, unavailability, district permissions and assignment collisions server-side.
- Preserve draft on 412, 409, 403 and 422; refresh canonical event and matrix after success.
- Test all failure modes and maintain >80% coverage.

Status: planned, implementation outstanding.
