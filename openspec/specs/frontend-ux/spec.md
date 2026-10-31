# frontend-ux Specification

## Purpose

Cross-cutting user-experience behaviour of the Vue SPA: feedback toasts, confirmation of destructive actions, empty states, sync status display, export URL copying and role-based contextual help.

## Requirements

### Requirement: User feedback and safe destructive actions
The SPA SHALL show success and error toasts for API actions, SHALL ask for confirmation in a dialog before delete, reject or cancel actions, and SHALL show explanatory empty states with a call to action for empty resource lists.

#### Scenario: User cancels a deletion
- **WHEN** the user clicks "Abbrechen" in a confirmation dialog
- **THEN** the action is not executed

### Requirement: Integration status and export URLs
The calendar integrations view SHALL show `last_synced_at` and a colour-coded status per integration; export token URLs SHALL be copyable to the clipboard with visual confirmation.

#### Scenario: Copy export URL
- **WHEN** the user clicks the copy button of an export URL
- **THEN** the URL is in the clipboard and a short confirmation appears

### Requirement: Role-based contextual help
Views with a help context SHALL show non-blocking help modules filtered by authentication status and role (anonymous users get registration guidance; viewers and planners get role-specific workflows; other roles' content is hidden). Users SHALL be able to hide individual modules and restore them; hidden state is a per-browser preference keyed by identity, help ID and context.

#### Scenario: Viewer sees planner help
- **WHEN** a viewer opens a view that has planner-only help modules
- **THEN** those modules are not shown

### Requirement: Session persistence of filters and sorting

Each view with filters or sorting, including the matrix and event list, SHALL retain its selected filter values and existing sort field, direction and options for the browser-tab session. Reopening the view, browser history navigation and reload SHALL restore valid settings. Controls and requested or displayed results SHALL reflect the same restored state.

#### Scenario: Return to the matrix

- **WHEN** the user selects a congregation text filter and enables group sorting in the matrix, opens another view and returns during the same session
- **THEN** the matrix restores both settings and displays the matching congregations in the selected order

#### Scenario: Return to the event list

- **WHEN** the user selects filters and, where provided, a sort field and direction in the event list, opens another view and returns during the same session
- **THEN** the event list restores those settings and displays the correspondingly filtered and sorted events

#### Scenario: Browser navigation and reload

- **WHEN** the user returns to a configured view using browser back or forward navigation, or reloads that view in the same tab
- **THEN** the valid filter and sorting settings remain selected and are applied to its results

### Requirement: Independent view and context settings

Session settings SHALL be isolated by authenticated user, view and applicable district or congregation context. Changing one view's settings SHALL NOT overwrite another view's settings. Settings SHALL NOT grant access to data outside the user's current permissions.

#### Scenario: Independent matrix and event list

- **WHEN** the user configures the matrix and then changes the event list's filters or sorting
- **THEN** each view retains its own last selected settings during the session

#### Scenario: Switch district or congregation

- **WHEN** the user switches to a different district or congregation context
- **THEN** the view uses that context's retained settings or its defaults if none exist
- **AND** returning to the previous context restores its still-valid settings

### Requirement: Session reset and valid restoration

Filter resets and sorting changes SHALL update session settings. Logout or identity change SHALL clear retained and active settings; a new independent tab SHALL use defaults. Invalid or inaccessible values SHALL fall back to defaults while valid fields remain intact. Missing, unavailable or malformed storage SHALL NOT prevent loading with defaults. Persistence across sessions and synchronization between tabs are not required.

#### Scenario: Explicit filter reset

- **WHEN** the user clears the filters and later reopens the view during the same session
- **THEN** the view retains the cleared filter state instead of restoring the earlier selection

#### Scenario: Logout or identity change

- **WHEN** the user logs out or the authenticated identity changes
- **THEN** previous retained and active filter and sorting settings are cleared
- **AND** the next user starts with default settings

#### Scenario: New session

- **WHEN** the user starts a new independent browser-tab session
- **THEN** views use their default filter and sorting settings

#### Scenario: Selected group is no longer available

- **WHEN** a retained filter refers to a group that was deleted or is no longer accessible
- **THEN** that filter falls back to a valid default
- **AND** other valid filters and sorting settings are preserved

#### Scenario: Session storage cannot be restored

- **WHEN** session storage is missing, unavailable or malformed
- **THEN** the view remains usable and loads with valid default settings

### Requirement: Globaler Bezirkskontext in der Navigation

Die Anwendung SHALL bei authentifizierten Benutzern auf jeder geschützten Ansicht den Namen des aktuell zugänglichen Bezirks in der Hauptnavigation anzeigen. Die Bezirksauswahl SHALL nur dann interaktiv sein, wenn die vom Backend für den aktuellen Benutzer freigegebene Bezirksliste mehr als einen Eintrag enthält. Matrix und Ereignisliste SHALL keinen eigenen Bezirksfilter anbieten und SHALL den globalen Kontext für ihre Datenabfragen verwenden.

#### Scenario: Genau ein zugänglicher Bezirk
- **WHEN** ein angemeldeter Benutzer genau einen zugänglichen Bezirk hat
- **THEN** erscheint dessen Name in der Hauptnavigation
- **AND** es gibt keine interaktive Bezirksumschaltung in Navigation, Matrix oder Ereignisliste

#### Scenario: Mehrere zugängliche Bezirke
- **WHEN** ein angemeldeter Benutzer mehrere zugängliche Bezirke hat
- **THEN** ist die aktuelle Bezirksauswahl in der globalen Navigation beschriftet und bedienbar
- **AND** nur diese zugänglichen Bezirke sind auswählbar
- **AND** der aktive Bezirk ist in jeder geschützten Ansicht erkennbar
- **AND** Matrix sowie Ereignisliste laden nach einem Wechsel Daten für den neu ausgewählten Bezirk

#### Scenario: Kein zugänglicher Bezirk
- **WHEN** ein angemeldeter Benutzer noch nicht freigeschaltet ist oder keine zugänglichen Bezirke hat
- **THEN** zeigt die Navigation keine Bezirksumschaltung
- **AND** es wird kein fremder Bezirk als aktueller Kontext verwendet

#### Scenario: Bezirksfreigabe entfällt
- **WHEN** die gespeichert ausgewählte Bezirks-ID nicht mehr in der zugänglichen Liste enthalten ist
- **THEN** wird ein gültiger Bezirk ausgewählt oder die Auswahl geleert, wenn die Liste leer ist
- **AND** eine unzulässige Auswahl kann nicht über den globalen Umschalter gesetzt werden

#### Scenario: Benutzerwechsel, Logout und verzögerte Antworten
- **WHEN** sich die Identität ändert, der Benutzer abmeldet oder eine ältere Bezirksabfrage erst nach dem Identitätswechsel antwortet
- **THEN** werden fremde Bezirksdaten und Auswahlwerte nicht übernommen
- **AND** die neue Identität beginnt mit ihrem eigenen berechtigten Bezirkskontext

#### Scenario: API-Abfrage der Bezirke schlägt fehl
- **WHEN** der Abruf der zugänglichen Bezirke fehlschlägt
- **THEN** wird kein zuvor gespeicherter Bezirk als weiterhin autorisiert ausgegeben

#### Scenario: Filter je Bezirkskontext
- **WHEN** der Benutzer den Bezirk global wechselt und anschließend zurückkehrt
- **THEN** werden gültige Matrix- und Ereignisfilter jeweils für den zugehörigen Bezirk wiederhergestellt
- **AND** ein Bezirkswechsel verändert die serverseitigen Rollen und Berechtigungsgrenzen nicht

### Requirement: Accessible progressive editing in event tables
All tabular overview screens SHALL keep input controls hidden in read mode and provide visible keyboard focus, accessible cell/editor labels and announced save/errors when a cell is edited. Edit controls SHALL work with touch, mouse and keyboard and SHALL not depend exclusively on hovering. Saving with a stale revision SHALL offer an accessible conflict explanation and a comparison/reload action; the draft MUST remain available until the user explicitly resolves or cancels it.

#### Scenario: Keyboard-only edit
- **WHEN** a keyboard user focuses an editable cell and activates it with Enter
- **THEN** the editor becomes focused and announces its field label and current value

#### Scenario: Stale-version feedback
- **WHEN** the server rejects a save with HTTP 412 due to a newer row revision
- **THEN** the editor announces the conflict and retains the draft for comparison or explicit cancellation

#### Scenario: Save feedback
- **WHEN** an inline cell change succeeds or fails
- **THEN** the interface communicates the result accessibly and preserves focus where practical

### Requirement: Application-wide table editing consistency
The SPA SHALL apply a common compact presentation, inline editor activation, keyboard navigation, save/cancel and error-feedback pattern to all table overviews with editable data, regardless of their underlying resource. Editing SHALL only be offered for authorised mutable fields; navigation and explicit domain actions SHALL remain distinct.

#### Scenario: Consistent cross-screen interaction
- **WHEN** a user moves between two different overview tables with editable cells
- **THEN** the same gestures, keyboard shortcuts, active-cell indicators and error states are used in both screens

#### Scenario: Derived field
- **WHEN** a cell displays a computed or protected value
- **THEN** it remains compact and readable without suggesting that it can be edited

### Requirement: Registration congregation choices SHALL match the current district
The public registration view MUST show congregation options only for the currently selected district. It SHALL immediately clear an obsolete congregation selection and options when the district changes. A delayed response or error from an obsolete request MUST NOT overwrite the current district's choices.

#### Scenario: Out-of-order district responses
- **WHEN** a user selects district A then district B and A's request completes after B's request
- **THEN** only district B's congregations remain available for selection

#### Scenario: District selection cleared while request is pending
- **WHEN** the district selection is cleared before a congregation request completes
- **THEN** the congregation selection and options remain empty, even if the previous request later completes

#### Scenario: Superseded request fails
- **WHEN** a previous district's request fails after the selected district's request succeeds
- **THEN** the error from the previous request does not clear the current district's congregations

### Requirement: Consistent error texts for failed requests
The SPA SHALL show the same German text per failure kind in views, dialogs and error toasts: the server's text (`detail` or `detail.message`) for 400, 404, 409 and 422, otherwise a fixed text per status, for an expired session and for an unreachable server. It MUST NOT show the raw status line, the response body, a 403 detail or a 5xx detail. Error texts SHALL use `role="alert"`.

#### Scenario: Taken name
- **WHEN** creating a congregation fails with 409 and the detail "Eine Gemeinde mit diesem Namen existiert bereits"
- **THEN** the dialog shows exactly that text

#### Scenario: Missing permission
- **WHEN** a request fails with 403, whatever its detail
- **THEN** the SPA shows "Für diese Aktion fehlt die Berechtigung."

#### Scenario: Server failure
- **WHEN** a request fails with a 5xx status
- **THEN** the SPA shows a request to try again later and none of the response body

### Requirement: Onboarding empty states
Empty lists that a new installation starts with SHALL explain the next step and, for users allowed to take it, offer it as an action: the first district, the first congregation of a district, the matrix of a district without congregations and the matrix without planned services. The matrix SHALL distinguish a district without congregations from a congregation or group filter without matches.

#### Scenario: District without congregations in the matrix
- **WHEN** the matrix of a district without congregations is shown and no congregation filter is set
- **THEN** it states that the district has no congregations yet instead of a filter hint
- **AND** offers "Gemeinde anlegen" only to district admins, which opens the new-congregation dialog of that district

#### Scenario: Group without congregations
- **WHEN** the selected group of the matrix has no congregations
- **THEN** it states that the group has no congregations and offers to show all groups

#### Scenario: Matrix without planned services
- **WHEN** the matrix shows congregations but no planned service in the selected range
- **THEN** it offers planners "Entwürfe erzeugen" for that range from the congregations' service times
- **AND** tells viewers that the planning creates the services
