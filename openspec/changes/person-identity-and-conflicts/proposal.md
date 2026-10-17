## Why

Persons can serve several congregations (a congregation leader of two congregations, an organist in two). A person must not be planned twice at the same time, but names are not identities: the same person can be entered twice (two leader records, free-text duty names) and defeat the conflict rules. Unit names (districts, congregations) should be unique.

## Decisions (made with the maintainer)

- One person, several congregations: a person–congregation–role relation replaces the single home congregation and special role (own step, larger migration).
- Name comparison for free names and new leaders: normalised full name (case, whitespace, accents, honorific titles ignored); a match yields a confirmable warning, never a block.
- Duties may reference an existing leader as a third identity (besides free name and linked account) so duties and service leadership are checked against each other.
- District and congregation names are unique, enforced in the API (409, case-insensitive), not by a database constraint; existing duplicates are left untouched.
- Error display is not unified (no shared alert component).

## What Changes

1. API-enforced unique names for districts (system-wide) and congregations (per district); event creation form validates end after start.
2. Duplicate hint with explicit override when creating a leader with an already known normalised name; conflict checks for organisational duties across congregations (identity key leader id > linked account > normalised name; hard block for strong identities, warning for names).
3. Matrix cells show planning conflicts (double booking, travel time, duties).
4. Person–congregation–role model replaces the single home congregation and special role.

## Capabilities

### Modified Capabilities
- `district-administration`: unique unit names; later steps extend leaders.
- `domain-conflict-engine` and `event-duties`: later steps.

## Impact

Backend routers/repositories and conflict rules; frontend forms, assignment dialog and matrix; step 4 adds a migration.

## Non-goals

- Database-level unique constraints for unit names; fuzzy matching; a unified error alert component.
