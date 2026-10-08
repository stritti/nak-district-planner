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
