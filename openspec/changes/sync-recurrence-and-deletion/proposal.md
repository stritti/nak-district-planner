## Why

Calendar sync (issue #465) queried providers without a window end, ignored
iCalendar recurrence, misread floating/all-day times as UTC and never detected
events removed from ICS feeds. Consequences: Microsoft Graph `calendarView`
rejects the query (400), CalDAV receives an invalid `time-range end=""`,
recurring services beyond their first occurrence are invisible, overrides of
one occurrence flip the hash of the whole series on every run, times shift by
1–2 hours, and deleted feed events stay active forever.

## What Changes

- Bounded sync window `[now - SYNC_WINDOW_PAST_DAYS (62), now + SYNC_WINDOW_FUTURE_MONTHS (24)]`
  passed as `from_dt`/`to_dt` to every connector; CalDAV omits unset bounds.
- ICS and CalDAV expand RRULE/RDATE series inside the window, honouring EXDATE
  and RECURRENCE-ID overrides (library `recurring-ical-events`, LGPL-3.0-or-later,
  used unmodified; dependency-review only denies GPL/AGPL).
- Occurrence identity is `UID::RECURRENCE-ID` (UTC `YYYYMMDDTHHMMSSZ`, or
  `YYYYMMDD` for all-day); non-recurring events keep their plain UID.
- Floating times and all-day dates are interpreted in `SYNC_DEFAULT_TIMEZONE`
  (default `Europe/Berlin`; District has no timezone field yet).
- ICS feeds are authoritative snapshots; reconciliation of missing events is
  limited to the queried window.
- Legacy series links (stored under the plain UID before this change) are
  re-keyed to the occurrence starting at the linked instance's start, so the
  planned slot is updated instead of cancelled.
- Expansion of untrusted feeds is bounded: sub-daily RRULEs are rejected, iteration
  is budgeted and in-window occurrences are capped (`SYNC_MAX_OCCURRENCES`, 5000).
- ICS events outside the window are reported as presence-only, so an event the
  provider moved out of the window is updated instead of cancelled. CalDAV filters
  server-side and cannot report them; there, an event moved beyond the window
  boundaries (>24 months ahead, >62 days back) is still reconciled as missing.
- A slot cancelled only because its event was missing from a snapshot is marked
  on the link (`deletion_reason`) and reactivated when the event reappears;
  manual and provider (STATUS:CANCELLED) cancellations are never undone.
- A snapshot with an unusable CalDAV resource or unparseable ICS VEVENT is not
  authoritative for that run: deletion reconciliation is skipped (warning, last sync error).
- Write-back (deviation/conflict resolution, internal delete) is refused for series
  occurrences before any provider call (HTTP 409). Links are recognized by their stored
  key shape; no migration.
- Occurrences carry `series_uid`/`recurrence_id` explicitly; the composed key is
  never parsed; overlong UIDs are hashed to keep keys within 500 characters.
- CalDAV refuses write-back (time update / delete) of a single occurrence,
  because it would rewrite or delete the whole series resource.

## Capabilities

### New Capabilities
- `calendar-sync`: window-bounded, recurrence-aware ingestion and deletion detection.

## Impact

- `app/adapters/calendar/ical_events.py` (new), ICS and CalDAV connectors.
- `app/application/sync_service.py` (window, legacy re-keying, window-bounded reconciliation).
- `app/config.py` settings; new dependencies `recurring-ical-events`, `python-dateutil` (explicit).
- Migration impact (no schema change): existing ICS/CalDAV series links that
  cannot be re-keyed (e.g. floating masters previously read as UTC) are missing
  from the snapshot and are cancelled per `delete_behavior` if their instance
  lies inside the window; the occurrences arrive as new candidates. Masters
  whose first occurrence is older than the window are left untouched. All-day
  and floating events receive one time-correcting update on the first run.
