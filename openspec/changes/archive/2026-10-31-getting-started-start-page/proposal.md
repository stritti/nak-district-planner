## Why

A new district has to go through seven screens in a fixed order before the congregations can subscribe to a calendar, but nothing shows that order or how far the district is. The root URL only redirected to the event list.

## What Changes

- New start page "Erste Schritte" at `/` with a status checklist for the selected district: Bezirk, Gemeinden mit Gottesdienstzeiten, Amtsträger, Entwürfe, Zuweisungen, Freigabe, Kalender-Abo. Draft, assignment and release status cover the next four weeks.
- Each step links its page; the action is offered only to the role that may take it, everyone else sees who takes the step. The first open step is highlighted.
- Users who plan no district keep landing on the event list; the login callback goes to `/`.
- Navigation link "Erste Schritte" for planners.

## Impact

- Frontend only; reads existing endpoints (districts, congregations, leaders, matrix, export tokens). Export tokens are only requested for district admins, matching the API guard.
