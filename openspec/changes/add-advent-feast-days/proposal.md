## Why

The computed church-feast import omits the four Advent Sundays, leaving the district calendars without these recurring Christian feast days. Adding them completes the church-feast coverage while reusing the existing holiday calendar behavior.

## What Changes

- Compute the dates of the 1st through 4th Advent for each imported year.
- Import each date as a confirmed, district-wide planning slot with category `Feiertag`, through both the scheduled and manual church-feast import paths.
- Keep repeated imports idempotent and verify Advent date calculation and slot creation in tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `holidays`: Include the four Advent Sundays among the computed church feast days and specify their calendar treatment.

## Impact

- Backend holiday calculation and import in `services/backend/app/application/feiertage_service.py`.
- Existing scheduled and manual import callers; no API, schema, dependency, or calendar-rendering changes are expected.
- Backend holiday service tests and the `holidays` OpenSpec capability.