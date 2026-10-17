## Why

The inline-editing change (`event-list-inline-cell-editing`) made event, assignment, leader, district and group writes conditional on a strong revision. Four editors were documented as follow-up and still overwrite concurrent changes silently: the congregation dialog, reminder configurations, event hooks and the organisational duties panel.

## What Changes

- Congregation dialog saves, reminder-configuration updates (including the active switch), event-hook updates (including the active switch) and duty assignment/suggestion changes require `If-Match` (428 missing, 412 stale) and return a fresh `revision`.
- Row locks serialise concurrent writers; the frontend sends the revision it read and, on 412/428, tells the user to reopen after the view was refreshed.

## Capabilities

### Modified Capabilities
- `event-list-inline-editing`: the dialog-writer revision contract now lists these editors.

## Impact

Backend routers/repositories for congregations, reminder configs, event hooks and event duties; their frontend API clients and views. The SPA is the only API client. No new writable fields and no permission changes.

## Non-goals

- Conditional writes for create/delete operations that carry no prior state.
- Cursor/ETag caching of read endpoints.
