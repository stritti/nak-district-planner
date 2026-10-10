## Why

Die Dienstplan-Matrix und die Ereignisliste enthalten eine Bezirk-Auswahl als lokalen Filter, obwohl der Bezirk ein übergeordneter Mandantenkontext ist. Für die meisten Nutzer ist nur ein Bezirk zugänglich. Eine wiederholte Auswahlliste suggeriert unnötige Optionen und macht den aktiven Mandanten außerhalb der beiden Ansichten nicht sichtbar.

## What Changes

- Die Hauptnavigation zeigt den aktiven Bezirk auf allen geschützten Ansichten, einschließlich schmaler Bildschirme.
- Nur wenn die serverseitig freigegebene Bezirksliste mindestens zwei Einträge hat, wird diese Anzeige zum Wechsel-Steuerelement.
- Bei genau einem Bezirk erscheint dessen Name ohne interaktiven Wechsel; ohne freigegebenen Bezirk erscheint keine Auswahl.
- Die lokalen Bezirksfilter entfallen in Dienstplan-Matrix und Ereignisliste (Liste, Woche, Monat). Der ausgewählte Bezirk bleibt im zentralen Store.
- Beim Wechsel laden aktive Ansichten die zugehörigen Daten neu. Bezirksspezifische View-Einstellungen werden weiterhin getrennt nach Benutzer und Bezirk gespeichert.
- Ungültige bzw. entzogene gespeicherte Bezirke werden durch einen freigegebenen Bezirk ersetzt. Logout, Benutzerwechsel und fehlgeschlagene Berechtigungsabfragen dürfen keinen fremden Bezirk erhalten.

## Capabilities

### Modified Capabilities
- `frontend-ux`: Globaler, berechtigungsbewusster Bezirkskontext und Wegfall von zwei redundanten lokalen Filtern.

## Impact

- Frontend: `AppNav.vue`, neue `DistrictContextSwitcher.vue`, `districts`-Store, `MatrixFilters.vue`, `EventListView.vue`.
- Backend: keine neuen Endpunkte oder Rechte. `GET /api/v1/districts` liefert bereits nur zugängliche Bezirke, bei Superadmin alle.
- Bestehende Session-Filter je Bezirk und Backend-Tenant-Isolation bleiben bestehen.
