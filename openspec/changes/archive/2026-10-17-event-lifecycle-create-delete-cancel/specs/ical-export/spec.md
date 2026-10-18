## ADDED Requirements

### Requirement: Stable cancellation notifications
A `CANCELLED` previously published planning slot SHALL remain exported to the same token scopes with its original UID, an incremented revision `SEQUENCE` and `STATUS:CANCELLED`. A public token SHALL continue to enforce confirmation and internal visibility rules, and a draft deleted before confirmation SHALL simply be absent.

#### Scenario: Released event cancelled after export
- **WHEN** a previously exported confirmed event is cancelled
- **THEN** its iCalendar event retains its UID and reports `STATUS:CANCELLED`
