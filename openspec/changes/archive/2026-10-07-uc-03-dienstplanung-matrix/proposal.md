## Why

Bezirksverantwortliche haben heute keinen konsolidierten Überblick, welche Gemeinden an welchen Sonntagen noch keinen Dienstleiter für den Gottesdienst haben. Das manuelle Abgleichen über separate Listen ist fehleranfällig und zeitaufwendig — Lücken (fehlende Zuweisung) werden zu spät bemerkt.

## What Changes

- Matrix-Ansicht im Frontend: X-Achse = Datum, Y-Achse = Gemeinde; Zellen zeigen Besetzungsstatus
- Spalten-Logik: Termine aus `service_times` der Gemeinden + importierte Feiertags-Events (`category=Feiertag`)
- Farbcodierung: LÜCKE (rot) = `category=Gottesdienst` AND kein `ServiceAssignment`; Besetzt (grün) = `ServiceAssignment` vorhanden; Leer (–) = kein geplanter Gottesdienst
- Klick auf Lücken-Zelle → Modal zur Auswahl eines Dienstleiters → erstellt/aktualisiert `ServiceAssignment`
- Feiertags-Namen im Spaltenkopf (grau, kursiv)
- API-Endpoint: `GET /api/v1/districts/{id}/matrix?from=&to=`
- `ServiceAssignment`-Endpunkte: `POST`, `PATCH`, `DELETE`

## Capabilities

### New Capabilities

- `service-matrix`: Backend-Logik und Frontend-Komponente für die Dienstplanungs-Matrixansicht mit Lücken-Visualisierung
- `service-assignment`: CRUD für `ServiceAssignment` (Verknüpfung Gottesdienst-Event ↔ Dienstleiter, Status: OPEN/ASSIGNED/CONFIRMED)

### Modified Capabilities

<!-- keine bestehenden Specs vorhanden -->

## Impact

- **Backend:** Neuer Matrix-Endpoint, neue `ServiceAssignment`-Repository-Implementierung, `_expected_dates`-Hilfslogik
- **Frontend:** Neue Vue-Komponente `MatrixView.vue`, Modal `AssignLeaderModal.vue`, Pinia-Store für Matrix-Daten
- **Datenbank:** Tabelle `service_assignment` bereits vorhanden (Alembic-Migration 0008); `service_times` JSONB auf `congregation`
- **Abhängigkeiten:** Keine neuen externen Abhängigkeiten
