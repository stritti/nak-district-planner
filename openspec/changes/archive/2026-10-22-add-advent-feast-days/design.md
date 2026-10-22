## Context

See `proposal.md` for motivation and `specs/holidays/spec.md` for the behavior contract. The holiday service already computes church feast dates and imports them as confirmed district-wide `Feiertag` planning slots. Both scheduled and manual imports call this service.

## Goals / Non-Goals

**Goals:**
- Add correctly dated, named Advent Sundays to the existing church-feast import.
- Preserve district-wide visibility and idempotent imports.

**Non-Goals:**
- Add a new holiday category, API, database field, external source, or calendar rendering behavior.
- Change the import schedule or the handling of public holidays.

## Decisions

- Calculate Advent from 25 December, not from Easter or an external holiday API. The 4th Advent is the Sunday strictly before 25 December; the 1st Advent is three weeks earlier, with the 2nd and 3rd Advent one and two weeks after the 1st. This directly follows the fixed Christmas calendar rule and handles years where Christmas itself falls on a Sunday.
- Add the four named dates (`1. Advent` through `4. Advent`) to the existing church-feast collection. Reuse its existing upsert path so each date remains a confirmed district-wide `Feiertag` slot and repeated imports remain idempotent. A separate importer would duplicate behavior without adding capability.
- Test known dates across years, slot metadata, and repeated-import behavior. Update existing expectations for the number of church-feast slots to include the four additional dates.

## Risks / Trade-offs

- Existing districts will not receive Advent slots until a scheduled or manual import runs after deployment. The scheduled task covers the current year and, from September onward, the next year; this is consistent with the existing holiday lifecycle.
- A code rollback does not remove already imported Advent slots. They are ordinary reference-data slots, and automatic deletion during rollback could remove data users may have relied on.

## Migration Plan

No database migration is required. Deploy the code and allow the existing scheduled task or an administrator-triggered import to create the new slots. Rolling back the code stops future Advent imports but leaves existing slots intact.
