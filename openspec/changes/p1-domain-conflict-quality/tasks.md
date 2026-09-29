## 1. Domain Conflict Engine

- [x] 1.1 `domain/planning/conflict_result.py`:
  - `Severity`-Enum: `PASS`, `WARN`, `BLOCK`
  - `ConflictResult`-Dataclass: `rule_id`, `severity`, `message` (DE+EN), `details` (dict)
- [x] 1.2 `domain/planning/conflict_rules.py`:
  - `no_double_booking`: Prüft auf zeitgleiche Zuweisungen → BLOCK
  - `travel_time_check`: Prüft Mindestabstand bei verschiedenen Gemeinden → WARN (konfigurierbar: `MIN_TRAVEL_MINUTES=30`)
  - `role_requirement_check`: Prüft Amtsstufe gegen Dienstanforderung → BLOCK
  - `leader_available`: Prüft Abwesenheiten im Zeitraum → BLOCK
  - `congregation_distance_check`: entfällt; Gemeindewechsel werden durch `travel_time_check` bewertet
- [x] 1.3 `domain/planning/conflict_service.py`:
  - `check(leader_id, start_time, end_time, congregation_id, required_role, existing_assignments, unavailability_periods) → list[ConflictResult]`
  - Orchestriert alle Regeln, sammelt Ergebnisse
- [x] 1.4 `ConflictContext`-Dataclass als Parameterobjekt
- [x] 1.5 Unit-Tests für jede Regel:
  - Double-Booking mit überlappenden Events
  - Double-Booking mit angrenzenden Events (kein Konflikt)
  - Travel-Time-Verletzung (30min < 45min → OK)
  - Travel-Time-Verletzung (15min < 30min → WARN)
  - Role-Requirement erfüllt/nicht erfüllt
  - Leader-Unavailability im Zeitraum/außerhalb
- [x] 1.6 Integrationstest: Conflict Service orchestriert korrekt

## 2. Leader Unavailability

- [x] 2.1 Domain-Modell `LeaderUnavailability` in `domain/models/leader_unavailability.py`
  - `id`, `leader_id`, `start_date`, `end_date`, `reason` (Enum: URLAUB, SPERRZEIT, FORTBILDUNG, SONSTIGES), `note`
- [x] 2.2 ORM-Modell `LeaderUnavailabilityModel` in `adapters/db/orm_models/`
- [x] 2.3 Alembic-Migration für `leader_unavailabilities`-Tabelle
- [x] 2.4 Repository `SqlLeaderUnavailabilityRepository` mit CRUD + Überschneidungsabfrage
- [x] 2.5 API-Router `routers/leader_unavailabilities.py` (CRUD, geschützt mit PLANNER+)
- [x] 2.6 Router in `main.py` registrieren

## 3. Integration in bestehende Services

- [x] 3.1 Assignment-Router: Vor Zuweisung `conflict_service.check()` aufrufen
  - Bei BLOCK → `ConflictError` → API 409 Conflict
  - Bei WARN → explizite Bestätigung über `confirm_warnings`, danach Assignment speichern
  - Die bestehende Codebasis hat keinen separaten `service_assignment_service.py`; die
    Integration erfolgt deshalb im Router mit einem getesteten Application-Adapter.
- [x] 3.2 Nicht anwendbar: Der Event-Erstellungspfad erzeugt nur PlanningSlot/EventInstance
  und akzeptiert keine `leader_id`. Leader-Zuweisungen entstehen ausschließlich über den
  Assignment-Router und werden dort durch Task 3.1 geprüft.
- [x] 3.3 API-Schema für Conflict-Response (409 Body mit Konfliktliste)
- [x] 3.4 Feature-Flag `CONFLICT_CHECK_ENABLED` (default: true)
- [x] 3.5 Konfiguration für `MIN_TRAVEL_MINUTES` in Settings ergänzen

## 4. Frontend: Konfliktanzeige

- [ ] 4.1 `ConflictBanner.vue`-Komponente: Zeigt Konflikte nach Severity (rot/gelb) mit Nachricht
- [ ] 4.2 Integration in Matrix-View: Zellen mit Konflikten markieren (Warnsymbol/Hintergrundfarbe)
- [ ] 4.3 Integration in ServiceAssignment-Dialog: Conflict-Banner vor Bestätigung
- [x] 4.4 BLOCK-Konflikte: Submit-Button deaktiviert + Begründung *(`canSubmit`-Guard + `aria-describedby`-Beschreibung; `title`-Tooltip auf deaktivierten Buttons ist browserabhängig unzuverlässig)*
- [x] 4.5 WARN-Konflikte: Bestätigungsmodal "Trotz Konflikt zuweisen?" *(bestehendes `ConfirmDialog.vue`, Retry mit `confirm_warnings: true`)*
- [x] 4.6 Pinia-Store für Konfliktstatus (z. B. `conflictStore`) *(`src/stores/conflict.ts`)*

## 5. Frontend: Abwesenheitsverwaltung

- [x] 5.1 `LeaderUnavailabilityForm.vue`: Formular für neue Abwesenheit (Leader-Auswahl, Datum, Grund)
  - Umgesetzt in `services/frontend/src/components/LeaderUnavailabilityForm.vue` (Leader-Select, Datum von/bis, Grund, Notiz, clientseitige Validierung Ende > Beginn)
  - Review-Korrekturen: Empty-State bei fehlenden Amtsträger:innen statt fehlerhafter Validierung, `required`/`aria-invalid` an Inputs, Fehlermeldung mit `role="alert"`/`aria-live`, einheitliche Leader-Anzeige via `leaderDisplayName`
- [x] 5.2 `LeaderUnavailabilityList.vue`: Liste bestehender Abwesenheiten mit Filter
  - Umgesetzt in `services/frontend/src/components/LeaderUnavailabilityList.vue` (Leader-Filter, Zeitraum-/Grund-/Notiz-Anzeige, Löschen mit Bestätigungsdialog)
  - Review-Korrekturen: Zeitraum-Formatierung und Leader-Namen aus geteilten Helpern (`formatUnavailabilityPeriod`, `leaderNameFromId`), `aria-label` am Löschen-Button
- [x] 5.3 API-Integration in Pinia-Store
  - Umgesetzt in `services/frontend/src/stores/leaderUnavailabilities.ts` + `services/frontend/src/api/leaderUnavailabilities.ts` (List/Create/Delete gegen `/api/v1/districts/{id}/leader-unavailabilities`)
  - Review-Korrekturen: Store-API nutzt den internen `districtId`-State (kein redundanter Parameter, kein stilles No-Op bei Mismatch), clientseitiger Leader-Filter statt ungenutztem Server-Filter-Pfad, `sortItems` mutiert Eingabearrays nicht mehr
- [x] 5.4 Navigation: Abwesenheiten in Leader-Detailansicht integrieren
  - Umgesetzt als „Abwesenheiten“-Tab in `services/frontend/src/views/LeadersAdminView.vue` mit Kalender-Icon-Aktion je Amtsträger:in (Filter + Formular vorausgewählt)

## 6. Frontend: Formular-Validierung und Fehlerzustände

- [ ] 6.1 Event-Formular: Validierung von Pflichtfeldern, Datumslogik (Ende > Start)
- [ ] 6.2 ServiceAssignment-Formular: Leader-Auswahl validieren, 409-Konflikte anzeigen
- [ ] 6.3 District-Congregation-Formulare: Eindeutigkeit prüfen (Name innerhalb Bezirk)
- [ ] 6.4 Einheitliche Fehleranzeige: `ErrorAlert.vue` für API-Fehler (400, 401, 403, 409, 500)
- [ ] 6.5 Onboarding-Erstnutzer: Leere-Zustände mit Handlungsaufforderung ("Noch keine Gemeinden")

## 7. E2E-Tests für Planungsflows

- [x] 7.1 Playwright-Test: Gottesdienst planen → Amtsträger zuweisen → Bestätigung *(bestehende `matrix-assignment.spec.ts` deckt den Happy-Path ab)*
  - Vorbereitung: Seed-Daten mit District + Congregation + Leader
  - Ausführung: Login → Matrix → Event anlegen → Leader zuweisen → Confirm
- [x] 7.2 Playwright-Test: Double-Booking provozieren → BLOCK-Konflikt *(`conflict-assignment.spec.ts`)*
  - Vorbereitung: Leader in zwei Events zur gleichen Zeit
  - Ausführung: Zweite Zuweisung → 409 → Konflikt-Banner sichtbar
- [x] 7.3 Playwright-Test: Wechselzeit-Konflikt → WARN + Bestätigung *(`conflict-assignment.spec.ts`: prüft Retry mit `confirm_warnings: true`)*
  - Vorbereitung: Leader in zwei Events mit <30min Abstand in verschiedenen Gemeinden
  - Ausführung: Zweite Zuweisung → WARN-Modal → Bestätigen → Erfolg
- [x] 7.4 Playwright-Test: Abwesenheit → Zuweisung blockiert *(`conflict-assignment.spec.ts`: `leader_available` BLOCK)*
  - Vorbereitung: Leader mit URLAUB im Zeitraum
  - Ausführung: Zuweisung → BLOCK-Konflikt angezeigt

## 8. Dokumentation

- [x] 8.1 Konfliktregeln in `docs/conflict-rules.md` dokumentieren
- [x] 8.2 Feature-Flag `CONFLICT_CHECK_ENABLED` in Betriebsdokumentation aufnehmen *(`docs/production-runbook.md` Abschnitt Production Guard)*
- [x] 8.3 E2E-Test-Setup in `tests/e2e/README.md` dokumentieren *(Setup läuft über `playwright.config.ts` mit `vite preview`; dokumentiert in `docs/conflict-rules.md` Abschnitt E2E-Tests)*
