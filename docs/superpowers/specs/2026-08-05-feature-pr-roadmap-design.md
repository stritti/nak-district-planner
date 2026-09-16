# Feature-PR-Roadmap (2026-08-05)

## Kontext

PR #242 (F-2: MatrixView-Refactor) ist gemerged. `main` ist sauber.
Vier OpenSpec-Changes haben offene Tasks, die sich zu sauberen, unabhängigen Feature-PRs bündeln lassen.
Jedes Feature bekommt einen eigenen Branch + PR, wird gemerged und verifiziert, bevor das nächste startet.

## Ziel

Alle vier OpenSpec-Changes abschließen:

- `p0-blitzer-production-readiness` → 19/19
- `uc-02-zyklischer-sync` → 10/10
- `uc-04-05-06-event-export-feiertage` → 17/17
- `planning-slot-hybrid-sync` → 7/7

## PR-Sequenz

| PR | Feature | Tasks | Scope | Abhängigkeiten |
|----|---------|-------|-------|----------------|
| A | Negative-Tests geschützte Routen (403) | p0 2.5 | Integrationstests + ggf. fehlende Guards fixen | — |
| B | Sync-Fehler sichtbar machen | uc-02 1.2, 3.5, 6.2, 7.2 | Migration `last_sync_error` + Sync-Logik + Integrationstest + UI-Anzeige | — |
| C | applicability-Filter Events-Endpoint | uc-04-05-06 3.2, 3.3, 3.4 | Backend: `GET /api/v1/events` + PUBLISHED-Filter + Test | — |
| D | Test-Vervollständigung Feiertage/Export | uc-04-05-06 2.10, 2.11, 4.7 | Nur Unit-Tests (Gauß, Idempotenz, UID-Stabilität, Anonymisierung) | — |
| E | Frontend-Event-Formular mit applicability | uc-04-05-06 5.2 | Vue-Formular (POST /events existiert) + Multi-Select | C (Feld-Semantik) |
| F | PlanningSeries-Slot-Service | planning-slot 3.1 | Backend-Service: Slots aus Serie generieren | — |
| G | Matrix-UI geplante/tatsächliche Zeit | planning-slot 5.1 | Vue-Matrix-Zelle erweitern | F (Datenquelle) |

## Reihenfolge-Logik

- Backend/DB/Tests vor UI: A–D, F sind Backend/Tests, E und G Frontend.
- Schnelle Wins zuerst: A (1 Task), dann B–D, dann E (Frontend), dann F/G (planning-slot, größter Architektur-Umfang).
- D ist rein test-lastig und low-risk → gut parallelisierbar mit C, aber sequenziell gemerged.
- Offene PRs #234/#208 werden vorab kurz auf Aktualität geprüft (nicht blockierend).

## PR-Details

### PR A — Negative-Tests geschützte Routen (p0 2.5)

**Akzeptanz:**
- Für jede geschützte Route existiert ein Integrationstest, der 403 bei falscher Rolle verifiziert.
- Tests laufen gegen Test-DB (Integrationstests, `docker compose run --no-deps --rm backend pytest tests/integration/`).
- Falls ein Test einen fehlenden Guard aufdeckt → Guard ergänzen, `docs/roles.md` konsistent halten.

**Verifikation:** `pytest tests/integration/ -v`, p0-Task 2.5 abhaken.

### PR B — Sync-Fehler sichtbar machen (uc-02)

**Akzeptanz:**
- Alembic-Migration: `last_sync_error` (TEXT, nullable) auf `calendar_integration`.
- SQLAlchemy-Modell + Pydantic-Schema um Feld erweitert.
- Sync-Service: bei Fehlschlag `last_sync_error` setzen, bei Erfolg leeren.
- Integrationstest: manueller Sync-Trigger (`POST /api/v1/calendar-integrations/{id}/sync`).
- Frontend `CalendarIntegrationsView.vue`: `last_sync_at` und `last_sync_error` anzeigen.

**Verifikation:** `pytest tests/unit/ tests/integration/`, vue-tsc/eslint, uc-02 1.2, 3.5, 6.2, 7.2 abhaken.

### PR C — applicability-Filter Events-Endpoint (uc-04-05-06)

**Akzeptanz:**
- `GET /api/v1/events` mit Gemeinde-Filter schließt Bezirks-Events ein, deren `applicability` die Gemeinde enthält (oder `"all"`).
- Nur `status=PUBLISHED` Bezirks-Events werden eingeblendet.
- Integrationstest: Bezirks-Event mit `applicability=["all"]` erscheint in Gemeindeansicht.

**Verifikation:** `pytest tests/integration/`, uc-04-05-06 3.2, 3.3, 3.4 abhaken.

### PR D — Test-Vervollständigung Feiertage/Export (uc-04-05-06)

**Akzeptanz:**
- Unit-Tests Gauß-Algorithmus mit bekannten Osterdaten 2025–2030.
- Unit-Tests Idempotenz (content_hash) und Bundesland-Filterung.
- Unit-Tests UID-Stabilität, Token-Validierung, Anonymisierung im ICS-Export.

**Verifikation:** `pytest tests/unit/`, uc-04-05-06 2.10, 2.11, 4.7 abhaken.

### PR E — Frontend-Event-Formular mit applicability (uc-04-05-06 5.2)

**Akzeptanz:**
- Event-Erstellungsformular im Frontend (POST /api/v1/events existiert bereits).
- `applicability`-Multi-Select (Gemeinde-Liste + "alle").
- Designer-Lane: UI/UX-Qualität.

**Verifikation:** vue-tsc/eslint, manueller UI-Test, uc-04-05-06 5.2 abhaken.

### PR F — PlanningSeries-Slot-Service (planning-slot 3.1)

**Akzeptanz:**
- Application-Service generiert Slots aus einer PlanningSeries (Wiederholung → konkrete Slots).
- Idempotent: erneute Generierung erzeugt keine Duplikate.
- Unit-Tests.

**Verifikation:** `pytest tests/unit/`, planning-slot 3.1 abhaken.

### PR G — Matrix-UI geplante/tatsächliche Zeit (planning-slot 5.1)

**Akzeptanz:**
- Matrix-Zelle zeigt geplante vs. tatsächliche Zeit (Datenquelle: F / vorhandene Deviation-Daten, 4.1 ist fertig).
- Designer-Lane für Layout/Anzeige.

**Verifikation:** vue-tsc/eslint, manueller UI-Test, planning-slot 5.1 abhaken.

## Arbeitsweise pro PR

1. Branch `feat/<pr-thema>` von `main`.
2. Implementierung + Tests.
3. Verifikation (Backend: pytest; Frontend: vue-tsc + eslint; Sicherheits-Scans nach Bedarf).
4. Commit, Push, PR gegen `main`.
5. Merge (Benutzer bestätigt) → nächster PR aus `main` heraus.

## Nicht Teil dieser Roadmap

- `code-quality` (33 offen), `p1-domain-conflict-quality` (39 offen), `improve-tenant-isolation` (60 offen) — spätere eigenständige PR-Blöcke.
- Dependabot-Bumps — laufen automatisch.
