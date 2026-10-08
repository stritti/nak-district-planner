## 1. Window

- [x] 1.1 Add `sync_window_past_days`, `sync_window_future_months`, `sync_default_timezone` settings
- [x] 1.2 Pass bounded `from_dt`/`to_dt` from `run_sync` to every connector
- [x] 1.3 CalDAV: omit unset `time-range` attributes (and the element when both are unset)

## 2. Recurrence and time zones

- [x] 2.1 Shared `expand_events` for ICS and CalDAV (RRULE, RDATE, EXDATE, RECURRENCE-ID)
- [x] 2.2 Occurrence identity `UID::RECURRENCE-ID`; plain UID for non-recurring events
- [x] 2.3 Floating and all-day times in the configured timezone
- [x] 2.4 CalDAV refuses write-back of a single occurrence

## 3. Deletion

- [x] 3.1 ICS connector is an authoritative snapshot
- [x] 3.2 Reconciliation skips instances outside the queried window
- [x] 3.3 Re-key legacy series links to the matching occurrence

## 4. Tests

- [x] 4.1 ICS fixtures: weekly series across DST, EXDATE, override, floating, all-day, far future
- [x] 4.2 Unit tests for connectors, window, reconciliation bounds, legacy re-keying
- [x] 4.3 PostgreSQL integration test: idempotent second run, removed event cancelled, out-of-window event kept

## 5. Review hardening (PR #483)

- [x] 5.1 Reactivate slots cancelled only by a snapshot gap when the event reappears
- [x] 5.2 Bound recurrence expansion (sub-daily rejection, iteration budget, `SYNC_MAX_OCCURRENCES`)
- [x] 5.3 Report ICS events outside the window as presence; update linked ones, never import or cancel them
- [x] 5.4 Hash overlong UIDs in occurrence keys (≤ 500 characters)
- [x] 5.5 Carry `series_uid`/`recurrence_id` explicitly; never parse the storage key; skip duplicate keys

## 6. Review hardening (0d600122)

- [x] 6.1 Incomplete CalDAV/ICS snapshots skip deletion reconciliation (`snapshot_complete`), with a warning and last sync error
- [x] 6.2 Refuse occurrence write-back in push paths before any connector call (409); no migration
- [x] 6.3 Keep UNTIL in the expansion budget, normalized to naive UTC
- [x] 6.4 One-day default only without DTEND and DURATION; explicit zero length stays

## 7. Review hardening (263a306f)

- [x] 7.1 Half-open window bounds for deletion reconciliation (`<=`/`>=`)
- [x] 7.2 Last sync error keeps the incomplete-snapshot note when events also failed
- [x] 7.3 Provider STATUS:CANCELLED replaces the snapshot-gap marker

## 8. Review hardening (20a3887d)

- [x] 8.1 CalDAV: confirm a missing resource via GET on its href before cancelling; Microsoft no longer authoritative
- [x] 8.2 VEVENT without UID makes the snapshot incomplete
- [x] 8.3 Open-ended events end one calendar day later in the event's time zone (DST-safe)
