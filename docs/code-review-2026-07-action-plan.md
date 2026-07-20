# Aktionsplan — Priorisierte Todo-Liste (aus Code Review Juli 2026)

> Basis: `docs/code-review-2026-07.md`. Findings sind hier nach möglichen, in sich geschlossenen
> PRs gruppiert — jede Gruppe kann unabhängig geplant, gebrancht und gemerged werden.
> Reihenfolge der Gruppen = Umsetzungsreihenfolge.

**Letztes Update:** 20.07.2026 — PR-1 bis PR-4 ✅ erledigt, siehe Abschnitt [Erledigte PRs](#-erledigte-prs).

---

## ✅ Erledigte PRs

### PR-1: Fix RBAC-Lücke `leaders.link-self` → ✅ Erledigt
> Findings: **B-1** · PR: [#209](https://github.com/stritti/nak-district-planner/pull/209)

- [x] `require_role_in_district(auth, Role.VIEWER, district_id)` vor `link_self_to_leader`,
      `unlink_self_from_leader`, `get_self_link` ergänzt
- [x] Einladungs-/Verifizierungsbindung geprüft: als Folge-Ticket ausgelagert (Scope der PR bewusst klein gehalten)
- [x] Regressionstest ergänzt: negativer Test (fremder Bezirk → 403), positiver Test (Mitglied → 200)
- [ ] `docs/rbac-completion-plan.md` / neue `docs/rbac-coverage.md` als erledigt vermerken

**Commit:** `9cb06f1` · **Merge:** PR [#209](https://github.com/stritti/nak-district-planner/pull/209) · **Owner:** @fixer

---

### PR-2: Toast-Feedback & ConfirmDialog verdrahten → ✅ Erledigt
> Findings: **F-1** · PR: [#210](https://github.com/stritti/nak-district-planner/pull/210)

- [x] `useToast()`/`stores/toast.ts` in zentralen API-Client und konsequent in allen Store-`catch`-Blöcken eingehängt
- [x] Erfolgsmeldungen nach kritischen Aktionen ergänzt (Leader, Sync, Registrierung, Export-Token)
- [x] `ConfirmDialog.vue` eingebunden bei:
  - [x] Kalender-Integration löschen
  - [x] Registrierung ablehnen
  - [x] Event stornieren
  - [x] Export-Token widerrufen
- [x] Vitest-Komponententests für Bestätigungsflüsse ergänzt
- [x] Playwright-E2E-Check "Abbrechen verhindert Löschung" für einen Flow

**Commit:** `08bcea4` · **Merge:** PR [#210](https://github.com/stritti/nak-district-planner/pull/210) · **Owner:** @designer + @fixer

---

### PR-3: Test-Coverage-Verifikation Auth/RBAC/Sync → ✅ Erledigt
> Findings: **B-4** · PR: [#212](https://github.com/stritti/nak-district-planner/pull/212)

- [x] Coverage-Report real ausgeführt: `app/adapters/auth/` — OIDC 92%, Claims-Validation 96%, JWT-Claims 89%
- [x] Testfälle für Rollen-Hierarchie × Scope-Type-Kombinationen ergänzt
- [x] Ergebnis in PR-Beschreibung dokumentiert

**Commit:** `11aba8c` · **Merge:** PR [#212](https://github.com/stritti/nak-district-planner/pull/212) · **Owner:** @fixer

---

### PR-4: RBAC-Guard-Konsolidierung (DRY-Refactor abschließen) → ✅ Erledigt
> Findings: **B-2** · PR: als Direkt-Commit (`5d6c43e`, `59f73eb`)

- [x] Verbleibende ~48 Stellen mit manuellem `try/except PermissionError`-Pattern auf
      `require_role_in_district()` / `require_role_in_congregation()` umgestellt
  - [x] `districts.py`
  - [x] `events_compat.py`
  - [x] `service_assignments.py`
  - [x] `planning_series.py`
  - [x] übrige Router (Restmenge)
- [ ] AST-Grep-/CI-Regel ergänzen, die neue `except PermissionError`-Vorkommen in Routern verhindert
- [x] Bestehende Tests grün (reines Refactoring, kein Verhaltenswechsel)

**Commits:** `5d6c43e`, `59f73eb` · **Owner:** @fixer

---

## 🔴 Noch offen — vor Go-Live (Production-Blocker)

> ⚠️ **Hinweis:** Die beiden ursprünglichen Production-Blocker (B-1, F-1) sind erledigt.
> Der Go-Live ist aus Code-Review-Sicht nicht mehr blockiert.

---

## 🟠 Hoch — kurz vor/nach Go-Live

### PR-5: Rate-Limiter-Fail-Open sichtbar machen (Observability)
> Findings: **B-5**

- [ ] Metrik/Zähler für "Rate-Limiter im Fail-Open-Modus" über `app/telemetry.py` ausleiten
- [ ] Alert-Schwelle/Dashboard-Hinweis dokumentieren (Ops-Runbook, `docs/production-runbook.md`)
- [ ] Bestehende `logger.warning(...)`-Stelle in `main.py:97-107` unverändert lassen, nur ergänzen

**Aufwand:** Gering · **Owner-Typ:** @fixer

---

### Entscheidungs-Ticket (kein Code-PR): `ExternalEventCandidate`/`SyncState` Scope für v1
> Findings: **B-3**

- [ ] Produktentscheidung einholen: Review-Workflow für externe Sync-Events in v1 erforderlich? (Ja/Nein)
- [ ] Falls Nein: Einschränkung explizit in `docs/use-cases.md` (UC-02) als "Phase 2" dokumentieren
- [ ] Falls Ja: eigenes Epic/PR-Gruppe planen (Domain-Modell, Repository, Review-UI — hoher Aufwand,
      nicht Teil dieses Aktionsplans)

---

## 🟡 Mittel — nächster Sprint

### PR-6: Dokumentation aktualisieren (alte Analyse-Docs bereinigen)
> Findings: **M-5**, **M-4**

- [ ] `docs/openspec-gap-analysis.md` als "historisch" kennzeichnen oder archivieren
- [ ] `docs/rbac-completion-plan.md` auf "Done" setzen (auth.py/system.py-Guards sind umgesetzt)
- [ ] `docs/architecture-status.md` aktualisieren: `ExternalEventLink` ✅ (teilweise), Audit-Logging ✅,
      Rate-Limiting ✅
- [ ] `docs/improvement-proposals.md` Abschnitte 5.1/5.5 korrigieren: Komponenten existieren,
      sind aber nicht verdrahtet (Verweis auf PR-2 statt "fehlt komplett")
- [ ] Neues `docs/rbac-coverage.md` erstellen (Router × Endpoint × erforderliche Rolle × Status) —
      verhindert erneutes manuelles Nachzählen bei künftigen Reviews

**Aufwand:** Gering · **Owner-Typ:** direkt (Doku, kein Code)

---

### PR-7: Pre-Go-Live-Verifikation (Audit-Log & Health-Check)
> Findings: **M-1**, **M-6**

- [ ] Stichprobe: Landen Rollenänderung, Registrierungs-Entscheidung, Export-Token-Erstellung
      tatsächlich im Audit-Log? (`application/audit_service.py` gegen echte DB-Einträge prüfen)
- [ ] `/api/health` prüfen: enthält DB- und Redis-Ping? Falls nicht, ergänzen
- [ ] Docker-Compose-Healthcheck auf `/api/health` referenzieren, falls noch nicht geschehen

**Aufwand:** Gering · **Owner-Typ:** @fixer

---

### PR-8: Sync-Service Aufräumen
> Findings: **M-2**, **M-3**

- [ ] `_get_connector()` in `sync_service.py` von if/elif-Kette auf Dict/Registry umstellen
      (`_CONNECTOR_MAP: dict[CalendarType, type[CalendarConnector]]`)
- [ ] `dict[str, int]`-Rückgaben durch typisiertes `@dataclass SyncResult` ersetzen
      (`created`, `updated`, `cancelled`, `errors`)
- [ ] Bestehende Aufrufer (`tasks.py`, Router) auf neue Signatur anpassen
- [ ] Tests in `test_sync_service.py` entsprechend anpassen (keine Verhaltensänderung, nur Typ)

**Aufwand:** Gering–Mittel · **Owner-Typ:** @fixer

---

## 🟢 Niedrig — Backlog

### PR-9: Frontend View-Aufteilung (Epic, mehrere Teil-PRs)
> Findings: **F-2**

- [ ] `MatrixView.vue` (1140 Zeilen) → `MatrixFilters.vue` / `MatrixTable.vue` / `AssignmentModal.vue`
- [ ] `LeadersAdminView.vue` (1124 Zeilen) → sinnvolle Unterkomponenten (Formular/Liste trennen)
- [ ] `EventListView.vue` (937 Zeilen) → `EventFilters.vue` / `EventTable.vue` / `EventFormModal.vue`
- [ ] `CalendarIntegrationsView.vue` (862 Zeilen) → `IntegrationCard.vue` / `IntegrationFormModal.vue`
- [ ] `DistrictsAdminView.vue` (778 Zeilen) → prüfen, ob Aufteilung sinnvoll (niedrigste Priorität dieser Gruppe)

**Aufwand:** Hoch, aber pro View unabhängig planbar · **Owner-Typ:** @designer (Struktur/Interaktion) + @fixer (mechanische Extraktion)
**Empfehlung:** Als 5 separate PRs führen, nicht als eine große Änderung.

---

### PR-10: Kleinere Clean-Code-Nacharbeiten
> Findings: **L-1**, **L-3**

- [ ] Docstrings für Enums ergänzen (`EventStatus`, `EventSource`, `ServiceAssignmentStatus`, u.a.)
- [ ] Kommentar in Celery-Tasks ergänzen, der `asyncio.run()`-Bridge-Pattern erklärt (kein async-Celery-Worker)

**Aufwand:** Gering · **Owner-Typ:** @fixer

---

### PR-11 (optional): Credential-Verschlüsselung als SQLAlchemy `TypeDecorator`
> Findings: **L-2**

- [ ] `EncryptedJSON`-`TypeDecorator` einführen, der `encrypt_credentials`/`decrypt_credentials`
      transparent beim Laden/Speichern anwendet
- [ ] Bestehende manuelle Aufrufe in `sync_service.py`, `calendar_integrations.py`-Router entfernen
- [ ] **Nur umsetzen, wenn Kapazität übrig ist** — aktueller Ansatz ist bereits korrekt und sicher

**Aufwand:** Mittel · **Priorität:** niedrig, rein optional

---

### Backlog-Eintrag (kein PR): Mobile-Ansicht der Matrix
> Findings: **L-4**

- [ ] Für v1 akzeptiert, keine Aktion nötig. Bei Bedarf später als eigenes Epic aufsetzen.

---

## Übersicht

| PR | Titel | Priorität | Status | Aufwand | Findings |
|---|---|---|---|---|---|
| PR-1 | RBAC-Lücke `leaders.link-self` fixen | 🔴 Sofort | ✅ Erledigt (#209) | Gering | B-1 |
| PR-2 | Toast & ConfirmDialog verdrahten | 🔴 Sofort | ✅ Erledigt (#210) | Mittel | F-1 |
| PR-3 | Coverage-Verifikation Auth/RBAC/Sync | 🟠 Hoch | ✅ Erledigt (#212) | Gering–Mittel | B-4 |
| PR-4 | RBAC-Guard-Konsolidierung (DRY) | 🟠 Hoch | ✅ Erledigt | Mittel | B-2 |
| PR-5 | Rate-Limiter-Observability | 🟠 Hoch | ❌ Offen | Gering | B-5 |
| — | Entscheidung ExternalEventCandidate/SyncState | 🟠 Hoch | ❌ Offen | – | B-3 |
| PR-6 | Doku-Aktualisierung | 🟡 Mittel | ❌ Offen | Gering | M-4, M-5 |
| PR-7 | Pre-Go-Live-Verifikation | 🟡 Mittel | ❌ Offen | Gering | M-1, M-6 |
| PR-8 | Sync-Service Aufräumen | 🟡 Mittel | ❌ Offen | Gering–Mittel | M-2, M-3 |
| PR-9 | Frontend View-Aufteilung (5 Teil-PRs) | 🟢 Niedrig | ❌ Offen | Hoch | F-2 |
| PR-10 | Kleinere Clean-Code-Nacharbeiten | 🟢 Niedrig | ❌ Offen | Gering | L-1, L-3 |
| PR-11 | Verschlüsselung als TypeDecorator (optional) | 🟢 Niedrig | ❌ Offen | Mittel | L-2 |
| — | Mobile Matrix (Backlog) | 🟢 Niedrig | ❌ Offen | – | L-4 |
