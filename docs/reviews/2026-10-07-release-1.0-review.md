# Release-Review 1.0 (Stand 2026-10-07)

> **Gegenstand:** `main` mit Version `1.0.0-rc.1` (Feature-Freeze) · **Tracker:** #476 · **OpenSpec-Abgleich:** #475

## 1. Umfang

Geprüft wurden Backend (FastAPI, Celery, SQLAlchemy/Alembic), Frontend (Vue 3/Pinia), Deployment (Docker Compose, nginx), CI-Workflows sowie die OpenSpec-Dokumentation. Grundlage der fachlichen Bewertung sind die mit #475 aus dem Code abgeleiteten Baseline-Specs in `openspec/specs/` (22 Capabilities). Nicht Gegenstand: Last- und Penetrationstests, Betrieb einer konkreten Produktionsumgebung.

## 2. Lokale CI-Ersatzumgebung

Die CI-Gates wurden in einer lokalen CI-Ersatzumgebung gegen `main` nachgestellt:

| Gate | Ergebnis |
|------|----------|
| Ruff (Backend-Lint) | ✅ ohne Befund |
| Backend-Integrationstests (PostgreSQL mit RLS) | ✅ 160 bestanden |
| Backend-Unit-Tests | ✅ 1231 bestanden, Coverage 86 % (Gate 80 %) |
| Frontend-Unit-Tests | ✅ 377 bestanden |
| `bun audit --audit-level=moderate` | ❌ schlägt fehl (`source-map-js`, siehe #456/#459) |
| `openspec validate --all` | ⚠️ nach #475: alle Baseline-Specs strikt gültig; 3 Changes mit offenen PRs noch ungültig (siehe Abschnitt 5) |

## 3. Gesamturteil

**Nicht freigabefähig für `v1.0.0`; RC-Phase fortsetzen.** Der funktionale Umfang ist vollständig und gut getestet, die Sicherheitsarchitektur (OIDC mit serverseitigem Refresh-Cookie, RBAC, RLS, Audit, CSRF, Rate-Limiting) ist umgesetzt. Vor der stabilen Version müssen die unten gelisteten Blocker geschlossen werden; die meisten haben bereits einen offenen PR.

## 4. Blocker

| Thema | Issue / PR | Kurzbeschreibung |
|-------|------------|------------------|
| Einzelbefunde des Release-Reviews | #461 – #469 | je ein Issue pro Befund; Details in den Issues |
| Release-Blocker | #455 | siehe Issue |
| CSRF nur über Header | #458 / PR #460 | Fallback auf das CSRF-Cookie entfernen (Double-Submit wirklich erzwingen) |
| Abhängigkeits-Audit | #456 / PR #459 | `source-map-js`-Advisory beheben, damit `bun audit` wieder grün ist |
| Deployment-Migrationen | #433 / PR #441 | Migrationen verlässlich im Deployment-Ablauf |
| Rate-Limit-Tenant-Grenze | #434 / PR #443 | Limits pro Tenant statt nur pro Nutzer/IP |
| Coverage-Umfang | #435 / PR #439 | Coverage über den vollständigen Anwendungsumfang messen |
| Architekturgrenze RC-2 | #437 / PR #444 | Abhängigkeitsrichtung erzwingen, Versionsquelle vereinheitlichen |
| OpenSpec-Baseline | #475 | Baseline-Specs, Archivierung, Doku-Abgleich, CI-Gate (dieser Stand) |
| Release-Blocker | #473 | siehe Issue |

## 5. Neue Befunde aus dem OpenSpec-Abgleich (#475)

1. **Kein Celery-Beat-Prozess im Compose-Stack.** `celery_app.py` definiert den Beat-Plan (Kalender-Sync alle 5 Minuten, Feiertagsimport, Entwurfs- und Serien-Generierung, Erinnerungen, Lücken-Scan, Versionsprüfung, Aufbewahrung), aber weder `docker-compose.yml` noch das Override startet `celery beat` bzw. `worker -B`. Ohne separaten Beat-Prozess laufen diese Aufgaben in Produktion nicht. → Blocker-Kandidat, Issue anlegen.
2. **Regression bei der Entwurfsgenerierung.** Die Zusicherung „verschobene Gottesdienste werden nicht am Ursprungstermin neu erzeugt“ hing an `events.generation_slot_key`, der mit dem Entfernen der `events`-Tabelle (Alembic 0125) entfallen ist. Heute wird nur nach Gemeinde/Datum/Uhrzeit dedupliziert.
3. **ICS-Export filtert nicht nach Status.** Abgesagte (`CANCELLED`) Planungseinträge werden ohne `STATUS:CANCELLED` exportiert; Leiter-Tokens filtern nur die Leiternamen, nicht die Termine. Zu prüfen, ob das beabsichtigt ist.
4. **`has_role_in_congregation`** berücksichtigt entgegen seinem Docstring keine Bezirksrollen; die Router kompensieren das durch einen Fallback auf `DISTRICT_ADMIN`. Docstring oder Verhalten angleichen.
5. **Ungültige aktive Changes mit offenen PRs:** `harden-production-supply-chain` und `server-held-oidc-refresh-token` haben je eine `MODIFIED`-Anforderung ohne Szenario (und müssen die Szenarien der Baseline übernehmen); `p1-domain-conflict-quality` hat keine Spec-Deltas. Das neue OpenSpec-Gate prüft deshalb vorerst nur die Baseline strikt; `validate --all` wird Gate, sobald diese PRs korrigiert sind.

## 6. Folgearbeiten (nicht blockierend)

- #470 – #474: Folge-Issues aus dem Review (Details in den Issues; #473 ist zugleich als Blocker gelistet).
- Backlog-Changes in OpenSpec: `caldav-adapter-hardening`, `calendar-provider-adapter-strategy`, `sync-state-policy-architecture`, `code-quality` (jetzt: Frontend-View-Zerlegung).
- Auswahl eines bestehenden Planungseintrags bei der Kandidatenprüfung (zurückgestellt aus `external-event-candidate-frontend`).
- `CHANGELOG.md` wird von release-please verwaltet und wurde bewusst nicht umsortiert.

## 7. Empfohlene Reihenfolge

1. Sicherheits- und Gate-Blocker: #456/#459 (Audit grün), #458/#460 (CSRF), #434/#443 (Tenant-Rate-Limit).
2. Betrieb: #433/#441 (Migrationen), Celery-Beat-Befund (Abschnitt 5.1), #435/#439 (Coverage).
3. Architektur und Spezifikation: #437/#444, danach #475; anschließend die offenen OpenSpec-Changes korrigieren und archivieren, `validate --all --strict` als Gate aktivieren.
4. Review-Einzelbefunde #461 – #469 abarbeiten.
5. #455 und #473 schließen, offene Verifikationspunkte von `prepare-v1-release-candidate` abhaken, danach Promotion auf `v1.0.0`.
