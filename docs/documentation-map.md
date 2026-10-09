# Dokumentationslandkarte (Source of Truth)

Dieses Dokument definiert, welche Unterlagen im Projekt verbindlich sind, welche
nur Planungsstand enthalten und welche als historischer Snapshot gelten.

## 1. Verbindliche Dokumentation

Diese Dokumente gelten als operative Quelle fuer Entwicklung und Betrieb.

- `README.md`: Einstieg, lokales Setup, Deployment-Basisablauf
- `docs/getting-started.md`: Lokaler Einstieg in die Doku und Arbeitsablaeufe
- `docs/use-cases.md`: Fachliche Kernablaeufe (UC-01 bis UC-06)
- `docs/roles.md`: Rollenmodell und Berechtigungsmatrix
- `docs/release-process.md`: SemVer-, Commit- und Release-Ablauf
- `docs/security-baseline.md`: Sicherheits-Baseline und Guardrails
- `docs/security-analysis.md`: Umfassende Security-Analyse mit Threat Modeling und Massnahmen
- `docs/production-runbook.md`: Betriebs- und Incident-Grundablaeufe
- `docs/production-compose.md`: Produktiv-Stack mit Traefik, Keycloak und GHCR-Images (`docker-compose.prod.yml`)
- `docs/schema.md`: Kritische DB-Constraints (FKs, Unique Constraints), bekannte Schema-Drift
- `docs/approval-workflow.md`: Benutzer-Onboarding, Freigabe-Workflow und IDP-Provisionierung
- `openspec/specs/*/spec.md`: Baseline der implementierten Capabilities (Ist-Stand, seit 2026-10-07)
- `openspec/architecture/overview.md`: Zielarchitektur (stabiler Rahmen)
- `openspec/architecture/implementation-roadmap.md`: Priorisierte Umsetzungsreihenfolge

## 2. Planungs- und Veraenderungsdokumentation

Diese Dokumente beschreiben geplante oder laufende Architektur-/Produkt-Aenderungen.

- `openspec/changes/*/proposal.md`: Problemstellung und Zielbild
- `openspec/changes/*/design.md`: Designentscheidungen
- `openspec/changes/*/tasks.md`: Umsetzungsaufgaben
- `openspec/changes/archive/*`: abgeschlossene bzw. ersetzte (SUPERSEDED) Changes
- `docs/improvement-proposals.md`: Analyse und priorisierte Verbesserungsoptionen
- `docs/reviews/*`: Release-Reviews mit Blocker- und Folgearbeitsliste (aktuell: `docs/reviews/2026-10-07-release-1.0-review.md`, Tracker #476)

Hinweis: Planungsdokumente sind nicht automatisch implementiert. Der
Implementierungsstatus wird in `docs/architecture-status.md` zusammengefasst.

## 3. Historische Dokumente

- `docs/archive/openspec-gap-analysis.md`: Gap-Analyse vom Juni 2026 (überholt durch die Baseline in `openspec/specs/`)

Regel: Historische Inhalte duerfen nicht als alleinige Grundlage fuer neue
Implementierung dienen. Bei Konflikten gilt Abschnitt 1.

## 4. Entscheidungsregel bei Widerspruechen

Wenn Aussagen kollidieren, gilt folgende Reihenfolge:

1. Sicherheits- und Betriebsregeln in `docs/security-baseline.md` und `docs/production-runbook.md`
2. Architektur- und Change-Regeln in `openspec/architecture/*`, der Baseline `openspec/specs/*` und aktiven `openspec/changes/*`
3. Operative Entwicklerhinweise in `README.md` und `docs/getting-started.md`
4. Historische Snapshots (nur Kontext)

## 5. Pflegeprozess

- Bei jeder strukturellen oder sicherheitsrelevanten Aenderung muss mindestens ein
  verlinktes, verbindliches Dokument aktualisiert werden.
- PRs mit Architektur- oder Security-Impact enthalten einen Abschnitt
  "Dokumentation aktualisiert".
- Veraltete Seiten werden entweder entfernt oder als Legacy klar getrennt
  ausserhalb der aktiven Navigationsstruktur abgelegt.
