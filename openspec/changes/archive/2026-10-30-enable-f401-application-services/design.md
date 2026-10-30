## Decision
Extend the pinned and isolated F401 quality gate from earlier migration steps to `app/application` as a directory. New application modules then inherit the gate automatically. Preserve the already protected registration route and all domain packages.

## Evidence: RED first
Commit `f065a9e` introduced only the additional gate. GitHub Actions [run 40086639329](https://github.com/stritti/nak-district-planner/actions/runs/40086639329) failed exactly at `Incremental F401 unused-import gate for reviewed modules`, listing five unused imports:
- `typing.Optional` in `app/application/csrf.py`.
- `SqlEventInstanceRepository`, `EventInstance`, `EventSource`, `EventVisibility` in `app/application/feiertage_service.py`.

## GREEN and runtime safety
Remove only those five imports. The holiday service now creates PlanningSlots instead of Events; its active imports `SqlPlanningSlotRepository`, `EventApprovalStatus`, `PlanningSlot`, and `PlanningSlotStatus` must not change. CSRF token signing and error handling are unchanged; no runtime code edits. The unchanged CI gate is expected to pass on the new head. Unit tests, exception handling, PostgreSQL RLS integration, >80% coverage, OpenSpec strict validation and security workflows remain required before merging.

## Alternatives rejected
A repo-wide F401 toggle would force changes across the large adapter/test surface without an isolated verification scope. Broad `noqa` exceptions would leave genuine lint defects unaddressed.
