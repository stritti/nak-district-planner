## 1. Advent Date Calculation

- [x] 1.1 Add calculation and names for the four Advent Sundays; verify unit tests cover the 2026 dates and a year when Christmas falls on Sunday.

## 2. Holiday Import

- [x] 2.1 Import each Advent Sunday through the existing church-feast upsert path as a confirmed district-wide `Feiertag`; verify slot metadata and idempotent second-import counts in unit tests.
- [x] 2.2 Run the focused holiday service test module and verify all tests pass.

## 3. OpenSpec Validation

- [x] 3.1 Validate the completed change against its proposal, holidays spec delta, design, and task list; verify OpenSpec reports no change-artifact errors.