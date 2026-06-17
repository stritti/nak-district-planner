## 1. Domain Conflict Engine

- [ ] 1.1 `domain/planning/conflict_result.py`:
  - `Severity`-Enum: `PASS`, `WARN`, `BLOCK`
  - `ConflictResult`-Dataclass: `rule_id`, `severity`, `message` (DE+EN), `details` (dict)
- [ ] 1.2 `domain/planning/conflict_rules.py`:
  - `no_double_booking`: Prüft auf zeitgleiche Zuweisungen → BLOCK
  - `travel_time_check`: Prüft Mindestabstand bei verschiedenen Gemeinden → WARN (konfigurierbar: `MIN_TRAVEL_MINUTES=30`)
  - `role_requirement_check`: Prüft Amtsstufe gegen Dienstanforderung → BLOCK
  - `leader_available`: Prüft Abwesenheiten im Zeitraum → BLOCK
  - `congregation_distance_check`: Verschiedene Gemeinden direkt nacheinander → WARN
- [ ] 1.3 `domain/planning/conflict_service.py`:
  - `check(leader_id, start_time, end_time, congregation_id, required_role, existing_assignments, unavailability_periods) → list[ConflictResult]`
  - Orchestriert alle Regeln, sammelt Ergebnisse
- [ ] 1.4 `ConflictContext`-Dataclass als Parameterobjekt
- [ ] 1.5 Unit-Tests für jede Regel:
  - Double-Booking mit überlappenden Events
  - Double-Booking mit angrenzenden Events (kein Konflikt)
  - Travel-Time-Verletzung (30min < 45min → OK)
  - Travel-Time-Verletzung (15min < 30min → WARN)
  - Role-Requirement erfüllt/nicht erfüllt
  - Leader-Unavailability im Zeitraum/außerhalb
- [ ] 1.6 Integrationstest: Conflict Service orchestriert korrekt

## 2. Leader Unavailability

- [ ] 2.1 Domain-Modell `LeaderUnavailability` in `domain/models/leader_unavailability.py`
  - `id`, `leader_id`, `start_date`, `end_date`, `reason` (Enum: URLAUB, SPERRZEIT, FORTBILDUNG, SONSTIGES), `note`
- [ ] 2.2 ORM-Modell `LeaderUnavailabilityModel` in `adapters/db/orm_models/`
- [ ] 2.3 Alembic-Migration für `leader_unavailabilities`-Tabelle
- [ ] 2.4 Repository `SqlLeaderUnavailabilityRepository` mit CRUD + Überschneidungsabfrage
- [ ] 2.5 API-Router `routers/leader_unavailabilities.py` (CRUD, geschützt mit PLANNER+)
- [ ] 2.6 Router in `main.py` registrieren

## 3. Integration in bestehende Services

- [ ] 3.1 `service_assignment_service.py`: Vor Zuweisung `conflict_service.check()` aufrufen
  - Bei BLOCK → `ConflictError` → API 409 Conflict
  - Bei WARN → Assignment speichern mit `warnings`-Attribut
- [ ] 3.2 `event_service.py`: Bei Event-Erstellung mit leader_id `conflict_service.check()` aufrufen
- [ ] 3.3 API-Schema für Conflict-Response (409 Body mit Konfliktliste)
- [ ] 3.4 Feature-Flag `CONFLICT_CHECK_ENABLED` (default: true)
- [ ] 3.5 Migration: Fehlende Konfiguration für `MIN_TRAVEL_MINUTES` in Settings ergänzen

## 4. Frontend: Konfliktanzeige

- [ ] 4.1 `ConflictBanner.vue`-Komponente: Zeigt Konflikte nach Severity (rot/gelb) mit Nachricht
- [ ] 4.2 Integration in Matrix-View: Zellen mit Konflikten markieren (Warnsymbol/Hintergrundfarbe)
- [ ] 4.3 Integration in ServiceAssignment-Dialog: Conflict-Banner vor Bestätigung
- [ ] 4.4 BLOCK-Konflikte: Submit-Button deaktiviert + Tooltip
- [ ] 4.5 WARN-Konflikte: Bestätigungsmodal "Trotz Konflikt zuweisen?"
- [ ] 4.6 Pinia-Store für Konfliktstatus (z. B. `conflictStore`)

## 5. Frontend: Abwesenheitsverwaltung

- [ ] 5.1 `LeaderUnavailabilityForm.vue`: Formular für neue Abwesenheit (Leader-Auswahl, Datum, Grund)
- [ ] 5.2 `LeaderUnavailabilityList.vue`: Liste bestehender Abwesenheiten mit Filter
- [ ] 5.3 API-Integration in Pinia-Store
- [ ] 5.4 Navigation: Abwesenheiten in Leader-Detailansicht integrieren

## 6. Frontend: Formular-Validierung und Fehlerzustände

- [ ] 6.1 Event-Formular: Validierung von Pflichtfeldern, Datumslogik (Ende > Start)
- [ ] 6.2 ServiceAssignment-Formular: Leader-Auswahl validieren, 409-Konflikte anzeigen
- [ ] 6.3 District-Congregation-Formulare: Eindeutigkeit prüfen (Name innerhalb Bezirk)
- [ ] 6.4 Einheitliche Fehleranzeige: `ErrorAlert.vue` für API-Fehler (400, 401, 403, 409, 500)
- [ ] 6.5 Onboarding-Erstnutzer: Leere-Zustände mit Handlungsaufforderung ("Noch keine Gemeinden")

## 7. E2E-Tests für Planungsflows

- [ ] 7.1 Playwright-Test: Gottesdienst planen → Amtsträger zuweisen → Bestätigung
  - Vorbereitung: Seed-Daten mit District + Congregation + Leader
  - Ausführung: Login → Matrix → Event anlegen → Leader zuweisen → Confirm
- [ ] 7.2 Playwright-Test: Double-Booking provozieren → BLOCK-Konflikt
  - Vorbereitung: Leader in zwei Events zur gleichen Zeit
  - Ausführung: Zweite Zuweisung → 409 → Konflikt-Banner sichtbar
- [ ] 7.3 Playwright-Test: Wechselzeit-Konflikt → WARN + Bestätigung
  - Vorbereitung: Leader in zwei Events mit <30min Abstand in verschiedenen Gemeinden
  - Ausführung: Zweite Zuweisung → WARN-Modal → Bestätigen → Erfolg
- [ ] 7.4 Playwright-Test: Abwesenheit → Zuweisung blockiert
  - Vorbereitung: Leader mit URLAUB im Zeitraum
  - Ausführung: Zuweisung → BLOCK-Konflikt angezeigt

## 8. Dokumentation

- [ ] 8.1 Konfliktregeln in `docs/conflict-rules.md` dokumentieren
- [ ] 8.2 Feature-Flag `CONFLICT_CHECK_ENABLED` in Betriebsdokumentation aufnehmen
- [ ] 8.3 E2E-Test-Setup in `tests/e2e/README.md` dokumentieren
