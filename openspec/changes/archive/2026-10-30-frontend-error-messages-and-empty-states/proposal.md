## Why
Failed requests reached the user as raw transport text such as `403 Forbidden: {"detail":"CSRF token missing"}`, worded differently in every view, and a 5xx detail could be shown verbatim. A district without congregations showed the matrix filter hint "Keine Gemeinde passt zu „“" with a reset button instead of the next step. These were the open form and error-state items of the archived change `p1-domain-conflict-quality` (tasks 6.1 to 6.5).

## What Changes
- `userMessage()` maps every failed request to one German text per status: the server's text (plain `detail` or `detail.message`) for 400, 404, 409 and 422, fixed texts for 401, 403, 412, 428, 429 and 5xx, and separate texts for an expired session and a lost connection. Views, stores and error toasts use it.
- `ErrorAlert.vue` (`role="alert"`) replaces the ad-hoc error paragraphs of views and dialogs.
- Empty states with a call to action: first district, first congregation of a district, and a matrix of a district without congregations (with "Gemeinde anlegen" for district admins).

## Capabilities
### Modified Capabilities
- `frontend-ux`: consistent error texts per HTTP status and onboarding empty states.

## Impact
Frontend only (`api/errors.ts`, `useToast`, stores, views, `ErrorAlert.vue`, `MatrixTable.vue`, `DistrictsAdminView.vue`) with unit tests. No API change.
