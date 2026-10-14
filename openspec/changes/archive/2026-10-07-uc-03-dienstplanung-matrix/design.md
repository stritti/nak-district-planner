## Context

Das Backend-Modell für `ServiceAssignment` und die Hilfslogik `_expected_dates()` sind bereits teilweise implementiert (Migration 0008+0009, `service_times` JSONB auf `congregation`). Der Matrix-Endpoint und das Vue-Frontend fehlen noch.

Die Matrix muss zwei Datumquellen kombinieren: geplante Gottesdienste aus `service_times` der Gemeinden + importierte Feiertags-Events (damit kirchliche Festtage immer als Spalten erscheinen, auch wenn die Gemeinde an dem Tag keinen regulären Gottesdienst hat).

## Goals / Non-Goals

**Goals:**
- GET `/api/v1/districts/{id}/matrix?from=YYYY-MM-DD&to=YYYY-MM-DD` → strukturierte Matrix-Antwort
- Spalten-Logik: Union aus `_expected_dates(service_times)` aller Gemeinden + Datumsangaben aller `category=Feiertag`-Events des Bezirks
- Zell-Status: `GAP` (rot, klickbar), `ASSIGNED` (grün), `EMPTY` (kein geplanter GD)
- ServiceAssignment-Endpunkte: `POST/PATCH/DELETE /api/v1/service-assignments`
- Vue-Komponente `MatrixView.vue`: Tabelle, Farbcodes, Feiertags-Label im Spaltenkopf
- Modal `AssignLeaderModal.vue`: Amtsträger-Suche und -Auswahl, Bestätigungs-Button
- Pinia-Store `useMatrixStore` für Matrix-Daten und Assignment-Aktionen

**Non-Goals:**
- Exportieren der Matrix als PDF/Excel
- Echtzeit-Updates (WebSocket) — Polling bei Modalschließen genügt
- Mobile-optimiertes Layout der Matrix

## Decisions

### API-Antwortformat
**Entscheidung:** Flat JSON-Struktur: `{ columns: [{ date, holiday_name? }], rows: [{ congregation_id, congregation_name, cells: [{ status, event_id?, assignment_id?, leader_name? }] }] }`.

Alternativ: vollständiger Event-Graph. Flat-Format reduziert die Frontend-Render-Logik erheblich.

### Spalten aus service_times + Feiertagen
**Entscheidung:** Backend berechnet die Spalten; Frontend zeigt nur das Ergebnis an.

**Begründung:** Vermeidet doppelte Logik im Frontend und hält die Vue-Komponente einfach. Änderungen an der Spalten-Logik (z. B. neue Feiertags-Quellen) wirken sofort für alle Clients.

### Nur `category=Gottesdienst` in Matrix
**Entscheidung:** Nur Events mit `category=Gottesdienst` werden für GAP-Erkennung herangezogen. Feiertags-Events (`category=Feiertag`) erzeugen Spalten, aber keine Zellen.

### Amtsträger-Quelle für Modal
**Entscheidung:** Vorerst Freitext-Eingabe (`leader_name`). Verknüpfung mit einer Personen-Entität ist spätere Phase.

## Risks / Trade-offs

- [Risiko] Großer Zeitraum (viele Gemeinden × viele Wochen) → langsame API → **Mitigation:** Standard-Zeitraum auf 4 Wochen begrenzen; Pagination für Spalten optional
- [Trade-off] Freitext-`leader_name` verhindert Deduplizierung bei Tippfehlern → bewusst akzeptiert für Phase 3; Personen-Modul folgt

## Migration Plan

1. Matrix-Endpoint implementieren (Backend)
2. ServiceAssignment-CRUD-Endpoints aktivieren
3. `MatrixView.vue` + `AssignLeaderModal.vue` implementieren
4. Integration-Tests mit Testbezirk + Testgemeinden
