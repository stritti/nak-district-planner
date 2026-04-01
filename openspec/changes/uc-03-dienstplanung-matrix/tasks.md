## 1. ServiceAssignment-CRUD (Backend)

- [x] 1.1 `ServiceAssignmentRepository`-Port und SQLAlchemy-Implementierung vorhanden
- [x] 1.2 `POST /api/v1/events/{event_id}/assignments` implementiert
      ⚠️ **Abweichung:** Endpoint-Pfad ist `/api/v1/events/{event_id}/assignments` (nicht `/api/v1/service-assignments` wie im Spec)
- [x] 1.3 `PUT /api/v1/events/{event_id}/assignments/{assignment_id}` implementiert (leader_name, status)
      ⚠️ **Abweichung:** HTTP-Methode `PUT` statt `PATCH`
- [ ] 1.4 `DELETE /api/v1/events/{event_id}/assignments/{assignment_id}` → **fehlt!**
- [x] 1.5 Pydantic-Schemas für ServiceAssignment Request/Response definiert
- [ ] 1.6 Unit-Tests für ServiceAssignment-CRUD

## 2. Matrix-Endpoint (Backend)

- [x] 2.1 `_expected_dates(service_times, from_date, to_date)` implementiert
- [x] 2.2 Feiertags-Events (`category=Feiertag`) in Spalten-Logik integriert, mit `holidays_map` in Response
- [x] 2.3 `MatrixResponse`-Pydantic-Schema definiert (dates, rows, cells mit is_gap/leader_name)
- [x] 2.4 `GET /api/v1/districts/{district_id}/matrix` implementiert
- [ ] 2.5 Standard-Zeitraum (4 Wochen) wenn `from_dt`/`to_dt` fehlen → **fehlt!** Parameter sind aktuell Pflichtfelder (`Query(...)`)
- [ ] 2.6 Integrations-Tests für Matrix-Endpoint (GAP, ASSIGNED, EMPTY)

## 3. Frontend — Matrixansicht

- [x] 3.1 Pinia-Store `useMatrixStore` (Matrix laden, Assignment erstellen/aktualisieren, persisted)
- [x] 3.2 `MatrixView.vue` mit Tabelle, Farbcodes (rot=Lücke, grün=Besetzt, –=leer), Zeitraum-Auswahl + Quick-Presets
- [x] 3.3 Feiertags-Namen im Spaltenkopf (grau, kursiv)
- [x] 3.4 Klick-Handler auf GAP-Zellen öffnet Modal (inline in `MatrixView.vue`)

## 4. Frontend — Zuweisung-Modal

- [x] 4.1 Zuweisung-Modal inline in `MatrixView.vue` implementiert (kein separates `AssignLeaderModal.vue`)
- [x] 4.2 Speichern-Button ruft `matrixStore.assign(eventId, leaderName)` → `POST /events/{id}/assignments`
- [x] 4.3 Nach Speichern: Matrix-Daten werden neu geladen, Modal schließt sich
- [ ] 4.4 Bestätigen-Button (`status=CONFIRMED`) im Modal → nicht implementiert

## 5. Navigation & Integration

- [x] 5.1 Route `/matrix` in Vue Router eingebunden
- [ ] 5.2 E2E-Test: Lücke erkennen → Modal → Zuweisung speichern → Zelle grün
