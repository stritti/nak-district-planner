# Code Review — Clean Code & Use-Case-Kohärenz (Juli 2026)

> **Stand:** 09.07.2026, Branch `fix/pip-audit-cve-joserfc` (HEAD `a920f40`)
> **Methodik:** Statische Analyse (Lesen von Domain-/Application-/Adapter-Code, gezielte `grep`/AST-Stichproben,
> Verifikation gegen bestehende Docs). Kein Laufzeit-Test, keine neue Testausführung.
> **Ziel:** Produktionsreife-Einschätzung mit priorisierten Findings, damit das System zeitnah produktiv gehen kann.

Dieses Dokument ersetzt **nicht** `docs/openspec-gap-analysis.md` und `docs/improvement-proposals.md`,
aktualisiert aber deren Kernaussagen anhand des tatsächlichen Codestands (siehe Abschnitt 5).
Viele dort als "fehlend" markierte Punkte sind inzwischen umgesetzt; einige sind es weiterhin nicht.

---

## 1. Executive Summary

**Einschätzung: Das System ist NICHT produktionsreif, ohne vorher 2 harte Blocker zu schließen.**
Beide Blocker sind mit geringem bis mittlerem Aufwand behebbar (geschätzt 1–3 Personentage zusammen).
Alle übrigen Findings sind entweder bekannte, akzeptable MVP-Einschränkungen oder mittel-/langfristige
Qualitätsverbesserungen, die den Go-Live nicht verzögern müssen.

| Schweregrad | Anzahl | Production-Blocker? |
|---|---|---|
| 🔴 Kritisch | 2 | Ja — vor Go-Live fixen |
| 🟠 Hoch | 5 | Nein, aber vor/kurz nach Go-Live adressieren |
| 🟡 Mittel | 6 | Nein — im nächsten Sprint |
| 🟢 Niedrig | 4 | Nein — Backlog |

**Die 2 Blocker:**
1. Autorisierungslücke bei `leaders.link-self` — jeder authentifizierte Nutzer kann sich beliebigem
   Amtsträger-Datensatz in beliebigem Bezirk zuordnen (Finding B-1).
2. Gebautes, aber nicht verdrahtetes UX-Sicherheitsnetz (Toast-Feedback + Bestätigungsdialoge) —
   destruktive Aktionen (Integration löschen, Registrierung ablehnen, Event stornieren) laufen ohne
   Rückfrage und ohne Fehler-Feedback (Finding F-1).

**Positiv hervorzuheben (bereits solide):**
- Hexagonale Architektur eingehalten — `domain/` ist tatsächlich frei von FastAPI-/SQLAlchemy-Importen (verifiziert).
- Rate-Limiting ist entgegen der alten Gap-Analyse bereits produktiv verdrahtet, inkl. pfadspezifischer Limits für `/api/v1/export/*`.
- Audit-Logging-Infrastruktur existiert und ist in `main.py` verdrahtet.
- Alembic-Migrationskette hat aktuell **genau einen Head** (`ae6c055cc051`) — kein Multiple-Head-Problem.
- Credential-Verschlüsselung wird konsistent über `crypto.py` genutzt, keine Klartext-Fundstellen.
- Google/Microsoft-Connector-Stubs sind im Frontend korrekt und ehrlich als "noch nicht implementiert" gekennzeichnet — kein Blocker, sondern sauber kommunizierte Einschränkung.
- E2E-Testabdeckung (Playwright) deckt die kritischen Flows breit ab (OIDC, geschützte Routen, Matrix-Assignment, Registrierung, Admin-CRUD).
- TypeScript-Hygiene im Frontend ist sehr gut: 0 Treffer für `any`, `@ts-ignore`, `@ts-expect-error`.

---

## 2. Kritische Findings (🔴 Production-Blocker)

### B-1 · Autorisierungslücke: `leaders.link-self` ohne Rollen-/Mitgliedschaftsprüfung

- **Kategorie:** Security / RBAC
- **Datei:** `services/backend/app/adapters/api/routers/leaders.py:152-198`
- **Befund:** `POST /districts/{district_id}/leaders/link-self`, `DELETE .../link-self` und
  `GET .../link-self` verwenden nur die Dependency `CurrentUser` (=
  `Annotated[User, Depends(get_current_active_user)]`, `deps.py:243`) — das prüft ausschließlich
  ein gültiges JWT, **keine** Mitgliedschaft oder Rolle im übergebenen `district_id`.
  Jeder authentifizierte Nutzer (auch ein frisch selbst-registrierter Nutzer ohne jede Freigabe)
  kann für **jeden** `district_id` + `leader_id` diesen Endpoint aufrufen. Einzige Prüfung ist, ob
  der Ziel-Leader bereits mit einem anderen `user_sub` verknüpft ist. D.h. jeder unverknüpfte
  Amtsträger-Datensatz in jedem Bezirk kann von jedem eingeloggten Nutzer "gekapert" werden.
  Alle anderen Endpoints in derselben Datei (`list/create/update/delete leaders`) nutzen korrekt
  `assert_has_role_in_district(...)` — das Self-Link-Trio wurde offenbar vergessen.
- **Auswirkung:** Governance-/Datenintegritätsrisiko — Identitätsübernahme eines Amtsträgers durch
  einen fremden, nicht autorisierten Nutzer, potenziell bezirksübergreifend.
- **Empfehlung:** Mindestens `require_role_in_district(auth, Role.VIEWER, district_id)` vor dem
  Self-Link ergänzen (Nutzer muss zumindest Mitglied des Bezirks sein). Idealerweise zusätzlich an
  einen Einladungsmechanismus koppeln (Analogie zu `invitations.py`, das aber für Dienst-Einladungen,
  nicht Nutzer-Onboarding ist — hier fehlt die Verbindung). Regressionstest ergänzen
  (`test_router_leaders_events_assignments.py`).
- **Aufwand:** Gering (< 1 Tag inkl. Test).

### F-1 · Toast-Feedback & Bestätigungsdialoge sind gebaut, aber nicht verdrahtet

- **Kategorie:** UX / Data-Safety
- **Dateien:** `services/frontend/src/stores/toast.ts`, `src/components/ToastContainer.vue`,
  `src/components/ConfirmDialog.vue`
- **Befund:** Beide Komponenten existieren (im Gegensatz zur veralteten Behauptung in
  `improvement-proposals.md`, dort seien sie "fehlend"), werden aber **nirgends im Frontend
  tatsächlich verwendet**:
  - `grep -rl "useToast\|toastStore" src/` findet nur die Store-/Container-Datei selbst — **keine**
    View oder kein Store ruft den Toast beim Erfolg/Fehler eines API-Calls auf (16 View-/Store-Dateien
    mit API-Aufrufen, 0 Toast-Aufrufe).
  - `grep -rl "ConfirmDialog" src/` liefert **0 Treffer außerhalb der Komponente selbst** —
    `ConfirmDialog.vue` wird in keiner View importiert/genutzt.
  - Praktische Folge: destruktive Aktionen (Kalender-Integration löschen, Registrierung ablehnen,
    Event stornieren, Export-Token widerrufen) laufen weiterhin **ohne Rückfrage** und ohne
    konsistentes Erfolgs-/Fehler-Feedback — genau das Risiko, das die alte Analyse schon beschrieb,
    nur dass jetzt totes Code-Gerüst existiert, das den Eindruck erweckt, das Problem sei gelöst.
- **Auswirkung:** Reales Risiko versehentlicher Datenverluste (z.B. Integration löschen ohne
  Rückfrage) kurz nach Go-Live — Support-/Vertrauensrisiko für eine Kirchenorganisation mit
  ehrenamtlichen Admin-Nutzern.
- **Empfehlung:** `ConfirmDialog.vue` an die destruktiven Aktionen in `CalendarIntegrationsView.vue`,
  `RegistrationView`/Registrierungs-Ablehnung, `ExportTokensView.vue`, Event-Stornierung koppeln.
  `useToast()`/Store in den zentralen API-Client (`src/api/client.ts`) oder zumindest in alle
  `catch`-Blöcke der Stores einhängen, damit Fehler nicht mehr stumm bleiben.
- **Aufwand:** Mittel (1–2 Tage für konsequente Verdrahtung an allen destruktiven Stellen).

---

## 3. Hohe Findings (🟠)

### B-2 · DRY-Refactor unvollständig: 48× dupliziertes `try/except PermissionError`-Pattern

- **Kategorie:** Clean Code (Wartbarkeit)
- **Dateien:** `app/adapters/api/routers/*.py` (überwiegend `districts.py`, `events_compat.py`,
  `service_assignments.py`, `planning_series.py`)
- **Befund:** `permissions.py` bietet bereits `require_role_in_district()` /
  `require_role_in_congregation()`, die die 403-Konvertierung kapseln (siehe Clean-Code-Skill). Trotz
  des Commits "Clean Code: Refactoring und DRY-Verbesserungen (#206)" nutzen nur **4 Dateien** diese
  Helfer, während **48 Stellen** weiterhin das manuelle
  `try: assert_has_role_in_district(...); except PermissionError as e: raise HTTPException(403, ...)`
  -Pattern enthalten. Der Refactor wurde offenbar begonnen, aber nicht flächendeckend abgeschlossen.
- **Auswirkung:** Kein akuter Bug, aber hohes Risiko für zukünftige Inkonsistenzen (z.B. vergessene
  403-Konvertierung bei neuen Endpoints, wie in Finding B-1 bereits passiert).
- **Empfehlung:** Verbleibende Router systematisch auf `require_role_in_*` umstellen; ein
  Lint-Check/AST-Grep-Regel als CI-Gate ergänzen, der neue `except PermissionError`-Vorkommen verhindert.
- **Aufwand:** Mittel (mechanisch, gut parallelisierbar durch mehrere `@fixer`-Läufe pro Router-Gruppe).

### B-3 · `ExternalEventCandidate` / `SyncState` weiterhin nicht implementiert

- **Kategorie:** Use-Case-Lücke (UC-02)
- **Befund:** Verifiziert — es existiert kein `external_event_candidate.py` und keine `SyncState`-Klasse
  im gesamten Backend. `ExternalEventLink` hingegen **existiert bereits** (Domain-Modell, ORM-Modell,
  Repository) — das ist neu gegenüber der alten Gap-Analyse. Neue extern importierte Events werden
  weiterhin direkt übernommen (`Event`/`PlanningSlot`, `source=EXTERNAL`), ohne manuellen Review-Schritt.
- **Auswirkung:** Kein Governance-Filter für unbekannte externe Kalenderquellen — das ist ein
  Produkt-/Fachentscheidung, keine Sicherheitslücke. Für einen MVP-Go-Live mit primär ICS/CalDAV-Quellen
  aus vertrauenswürdigen internen Kalendern ist das vertretbar, **muss aber explizit als bekannte
  Einschränkung gegenüber den Fachverantwortlichen kommuniziert und freigegeben werden**, bevor produktiv
  gegangen wird — nicht stillschweigend verschieben.
- **Empfehlung:** Produktentscheidung einholen: "Ship ohne Review-Workflow für v1" ja/nein.
  Falls ja: in `docs/use-cases.md` als "Phase 2" explizit dokumentieren, damit es nicht als Bug gemeldet wird.
- **Aufwand:** Für Sign-off: keiner. Für Implementierung (falls gefordert): Hoch.

### F-2 · Frontend-Views deutlich größer als in `improvement-proposals.md` dokumentiert

- **Kategorie:** Clean Code (Wartbarkeit)
- **Befund:** Aktuelle Zeilenzahlen (verifiziert per `wc -l`) weichen stark von der alten Doku ab:

  | View | Alte Doku | Aktuell |
  |---|---|---|
  | `MatrixView.vue` | 440 | **1140** |
  | `LeadersAdminView.vue` | – | **1124** |
  | `EventListView.vue` | 870 | **937** |
  | `CalendarIntegrationsView.vue` | 852 | **862** |
  | `DistrictsAdminView.vue` | – | **778** |

  Die Views sind seit der letzten Analyse weiter gewachsen statt aufgeteilt worden. Das ist keine
  neue Erkenntnis im Prinzip, aber die alte Doku unterschätzt das Ausmaß erheblich — sollte nicht als
  "schon bekannt, niedrige Priorität" abgetan werden.
- **Auswirkung:** Erschwert Review, Testbarkeit und Onboarding neuer Entwickler. Kein funktionaler
  Blocker für Go-Live.
- **Empfehlung:** Nach Go-Live priorisiert aufteilen, beginnend mit `MatrixView.vue` (größte Datei,
  zentrale Fachlogik) in `MatrixFilters.vue` / `MatrixTable.vue` / `AssignmentModal.vue` — deckt sich
  mit der bereits vorhandenen Empfehlung in `improvement-proposals.md` §4.1, nur mit aktualisierten Zahlen.
- **Aufwand:** Hoch, aber gut in einzelne `@designer`/`@fixer`-Lanes pro View aufteilbar.

### B-4 · Testabdeckung kritischer Auth-/RBAC-Module unklar/niedrig

- **Kategorie:** Tests
- **Datei:** `tests/unit/test_auth_permissions_jwt_claims.py` (nur 4 Testfunktionen)
- **Befund:** `docs/coverage-strategy.md` fordert ≥90% Zeilenabdeckung für Auth/RBAC/Sync. Die
  zentrale Permissions-/JWT-Claims-Testdatei enthält nur 4 Testfälle — das wirkt niedrig gemessen an
  der Kritikalität und Komplexität des Moduls (mehrere Rollen × zwei Scope-Typen × Superadmin-Sonderfall).
  `test_cross_tenant_isolation.py` ist mit 21 Tests dagegen gut abgedeckt — die Verteilung ist uneinheitlich.
  Dies ist eine Einschätzung anhand der Testanzahl, **keine tatsächliche Coverage-Messung** — vor
  Go-Live sollte `pytest --cov=app/adapters/auth` real ausgeführt werden, um die Prozentzahl zu verifizieren.
- **Empfehlung:** Coverage-Report für `app/adapters/auth/` vor Go-Live tatsächlich ziehen (CI-Artefakt
  sollte das bereits enthalten); falls < 90%, gezielt Testfälle für Rollen-Hierarchie, Scope-Type-Kombinationen
  und die in Finding B-1 gefundene Lücke ergänzen.
- **Aufwand:** Gering (Messung) bis Mittel (Nachbesserung).

### B-5 · Rate-Limiter ist "fail-open" ohne Monitoring/Alerting

- **Kategorie:** Security / Robustheit
- **Datei:** `services/backend/app/main.py:97-107`
- **Befund:** Bewusste, dokumentierte Design-Entscheidung: Wenn Redis beim Start/während der Laufzeit
  nicht erreichbar ist, werden Requests **ohne** Rate-Limiting durchgelassen (`check_rate_limit`
  liefert `allowed=True` im Fehlerfall). Das ist pragmatisch, aber es gibt aktuell keine sichtbaren
  Alerts/Metriken, die einen Betreiber informieren, wenn dieser Zustand eintritt — insbesondere
  relevant für den öffentlichen `/api/v1/export/*`-Endpoint.
- **Empfehlung:** Log-Zeile (bereits vorhanden: `logger.warning(...)`) zusätzlich als Metrik/Alert
  ausleiten (z.B. OpenTelemetry-Zähler, da `app/telemetry.py` bereits existiert), damit Redis-Ausfälle
  operativ sichtbar sind. Kein Blocker, aber vor Go-Live einplanen, falls Observability-Stack aktiv genutzt wird.
- **Aufwand:** Gering.

---

## 4. Mittlere Findings (🟡)

| # | Titel | Kategorie | Ort | Kurzbeschreibung | Aufwand |
|---|---|---|---|---|---|
| M-1 | Audit-Logging-Vollständigkeit nicht verifiziert | Security | `middleware/audit.py`, `application/audit_service.py` | Middleware + Service sind verdrahtet (verifiziert), aber welche konkreten Mutationen tatsächlich geloggt werden, wurde nicht im Detail geprüft. Vor Go-Live stichprobenartig verifizieren, dass sicherheitsrelevante Aktionen (Rollenänderung, Registrierungs-Entscheidung, Export-Token-Erstellung) im Audit-Log landen. | Gering |
| M-2 | Connector-Factory weiterhin if/elif-Kette | Clean Code | `application/sync_service.py:45-53` | Wie in `improvement-proposals.md` §2.1 beschrieben, weiterhin nicht auf Dict/Registry umgestellt. Bereits als niedrige Priorität eingestuft — bestätigt. | Gering |
| M-3 | `dict[str, int]`-Rückgaben statt typisierter Result-Objekte | Clean Code | `application/sync_service.py`, ggf. weitere Services | Wie in `improvement-proposals.md` §4.3 beschrieben, weiterhin nicht umgesetzt. Bestätigt, niedrige Priorität. | Gering |
| M-4 | Uneinheitliche RBAC-Guard-Dichte je Router | Clean Code / Security | Router-weit | `registrations.py` (14 Endpoints/6 Guards) und `leaders.py` (8/5) wirken auf den ersten Blick unterversorgt; bei Detailprüfung sind die "fehlenden" Fälle **bis auf Finding B-1** bewusst öffentliche/self-service Endpoints. Empfehlung: diese Analyse als Dokument festhalten (`docs/rbac-coverage.md` gemäß `rbac-completion-plan.md` Task 1.4.6), damit zukünftige Reviewer nicht erneut manuell nachzählen müssen. | Mittel |
| M-5 | Alte Analyse-Dokumente teils veraltet, aber noch aktiv verlinkt | Dokumentation | `docs/openspec-gap-analysis.md`, `docs/rbac-completion-plan.md` | Beide referenzieren Zustände (z.B. "auth.py 0 RBAC-Checks"), die inzwischen behoben sind. Verwirrungsgefahr für neue Entwickler. | Gering |
| M-6 | Health-Check-Tiefe nicht verifiziert | Ops | `/api/health` | In `improvement-proposals.md` als "fehlend" markiert; nicht im Detail geprüft, ob DB-/Redis-Ping enthalten sind. Vor Go-Live kurz verifizieren, da Docker-Healthchecks/Orchestrierung davon abhängen. | Gering |

---

## 5. Niedrige Findings (🟢)

| # | Titel | Kategorie | Kommentar |
|---|---|---|---|
| L-1 | Enum-Werte ohne Docstrings | Clean Code | Wie in `improvement-proposals.md` §4.5 beschrieben — weiterhin gültig, kosmetisch. |
| L-2 | Verschlüsselung über manuelle Decorator-Aufrufe statt `TypeDecorator` | Clean Code | Aktueller Ansatz ist korrekt und sicher (verifiziert: 3 konsistente Nutzungsstellen). Migration zu `TypeDecorator` bleibt optional. |
| L-3 | Celery-`asyncio.run()`-Bridge weiterhin undokumentiert | Clean Code | Kein neuer Fund, Empfehlung aus alter Doku weiterhin gültig. |
| L-4 | Mobile-Ansicht der Matrix weiterhin nicht optimiert | UX | Bestätigt weiterhin gültig, für v1 akzeptabel (Desktop-Zielgruppe: Bezirksadmins am PC). |

---

## 6. Use-Case-Kohärenz — Ist-Zustand (verifiziert)

| Use Case | Domain | Application | API | Frontend | Tests | Status |
|---|---|---|---|---|---|---|
| UC-01 Kalender-Anbindung | ✅ | ✅ (ICS/CalDAV voll, Google/MS nur Fetch-Logik ohne OAuth-Handshake) | ✅ | ✅ (UI kennzeichnet Google/MS ehrlich als "noch nicht implementiert") | 🟡 (Connector-Tests vorhanden, OAuth-Flow selbst nicht testbar, da nicht implementiert) | 🟢 Für ICS/CalDAV produktionsreif |
| UC-02 Zyklischer Sync | ✅ | ✅ (Hash-Dedup vorhanden) | – (Celery) | ✅ (`SyncStatusCard.vue` zeigt Status) | ✅ (10 Tests) | 🟡 Funktional ok, aber ohne Review-Workflow (B-3) |
| UC-03 Dienstplanung-Matrix | ✅ (`PlanningSlot`/`EventInstance`) | ✅ (`_expected_times`/`_actual_times`/`has_deviation` sauber faktorisiert) | ✅ | ✅ (`DeviationIndicator.vue`) | ✅ (8+ Tests) | 🟢 Solide |
| UC-04 Event-Verteilung | ✅ | ✅ | ✅ | ✅ | 🟡 (nicht im Detail neu verifiziert) | 🟢 Laut vorheriger Analyse vollständig |
| UC-05 Sicherer ICS-Export | ✅ | ✅ | ✅ (+ Rate-Limit auf `/export/*` verifiziert) | ✅ (Copy-to-Clipboard vorhanden — alte Doku-Kritik überholt) | 🟡 | 🟢 Solide |
| UC-06 Feiertags-Import | ✅ | ✅ | ✅ | ✅ | 🟡 | 🟢 Laut vorheriger Analyse vollständig |

---

## 7. Status alter Analyse-Dokumente

| Dokument | Empfehlung |
|---|---|
| `docs/openspec-gap-analysis.md` | **Veraltet in wesentlichen Punkten.** Aussagen zu "0 RBAC-Checks in auth.py/system.py", "kein Rate-Limiting", "kein Audit-Logging", "kein Toast-System" sind überholt — diese existieren inzwischen (auch wenn Toast/ConfirmDialog nicht verdrahtet sind, s. F-1). Empfehlung: als "historisch" kennzeichnen oder archivieren, nicht mehr als aktuellen Sollzustand zitieren. |
| `docs/rbac-completion-plan.md` | **Größtenteils erledigt.** `/access`-Guard in `auth.py` ist implementiert, `system.py` hat Guards. Als "Done" markieren oder archivieren; verbleibender offener Punkt daraus (Task 1.4.6, RBAC-Coverage-Dokument) bleibt sinnvoll (siehe M-4). |
| `docs/improvement-proposals.md` | **Teilweise veraltet, teilweise weiterhin exakt zutreffend.** View-Größen (F-2), Connector-Factory (M-2), Result-Objekte (M-3), Enum-Docstrings (L-1) weiterhin gültig. Toast/Confirm-Dialog-Abschnitte (5.1, 5.5) müssen aktualisiert werden: Komponenten existieren nun, sind aber nicht verdrahtet (F-1) — das ist ein anderes Problem als "existiert nicht". |
| `docs/architecture-status.md` | Sollte aktualisiert werden: `ExternalEventLink` ist inzwischen ❌→teilweise ✅ (Modell/Repo vorhanden), Audit-Logging und Rate-Limiting sollten von 🟡/❌ auf ✅ angehoben werden. |

---

## 8. Empfohlene Reihenfolge bis Produktivgang

1. **Sofort (vor Go-Live):** B-1 fixen (Aufwand < 1 Tag), F-1 verdrahten (1–2 Tage), B-4 Coverage-Report ziehen und ggf. nachbessern.
2. **Vor/kurz nach Go-Live:** B-3 Produktentscheidung einholen und dokumentieren, M-1 Audit-Log-Stichprobe verifizieren, M-6 Health-Check-Tiefe verifizieren.
3. **Erster Sprint danach:** B-2 (DRY-Refactor abschließen), M-4 (RBAC-Coverage-Dokument), Doku-Updates (M-5, Abschnitt 7).
4. **Backlog:** F-2 (View-Aufteilung), M-2/M-3, L-1 bis L-4.

**Fazit:** Kein architektonischer Neubau nötig. Die Hexagonal-Architektur ist sauber eingehalten,
Security-Grundpfeiler (Verschlüsselung, Tenant-Isolation, Rate-Limiting, Audit-Logging) sind vorhanden.
Mit den zwei kritischen Fixes (B-1, F-1) und einer Coverage-Verifikation (B-4) ist ein verantwortbarer
Produktivgang zeitnah möglich.
