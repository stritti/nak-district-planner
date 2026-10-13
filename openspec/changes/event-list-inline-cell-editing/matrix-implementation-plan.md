# Matrix inline editing implementation plan

Base: feat/inline-editing-safe-events (#576).

- Preserve existing MatrixTable navigation and AssignmentModal workflows.
- Expose versioned assignment read model and conditional mutation contract; reject missing If-Match with 428, stale writes with 412, domain conflicts with 409.
- Respect district role checks, cross-district isolation, unavailability and assignment conflict acknowledgments.
- Inline-edit only independently safe fields; preserve confirmation dialogs for destructive changes.
- Test keyboard, touch, stale version, missing permission, conflicts, double submission and >80% coverage.

Status: planned, implementation outstanding.
