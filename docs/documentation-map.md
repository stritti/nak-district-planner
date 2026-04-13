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
- `docs/production-runbook.md`: Betriebs- und Incident-Grundablaeufe
- `openspec/architecture/overview.md`: Zielarchitektur (stabiler Rahmen)
- `openspec/architecture/implementation-roadmap.md`: Priorisierte Umsetzungsreihenfolge

## 2. Planungs- und Veraenderungsdokumentation

Diese Dokumente beschreiben geplante oder laufende Architektur-/Produkt-Aenderungen.

- `openspec/changes/*/proposal.md`: Problemstellung und Zielbild
- `openspec/changes/*/design.md`: Designentscheidungen
- `openspec/changes/*/tasks.md`: Umsetzungsaufgaben
- `docs/improvement-proposals.md`: Analyse und priorisierte Verbesserungsoptionen

Hinweis: Planungsdokumente sind nicht automatisch implementiert. Der
Implementierungsstatus wird in `docs/architecture-status.md` zusammengefasst.

## 3. Historische Dokumente

Diese Dokumente dienen als Kontext zu abgeschlossenen oder ersetzten Phasen.

- `docs/auth-keycloak.md` (explizit veraltet)

Regel: Inhalte aus historischen Dokumenten duerfen nicht als alleinige Grundlage fuer
neue Implementierung dienen. Bei Konflikten gilt Abschnitt 1.

## 4. Entscheidungsregel bei Widerspruechen

Wenn Aussagen kollidieren, gilt folgende Reihenfolge:

1. Sicherheits- und Betriebsregeln in `docs/security-baseline.md` und `docs/production-runbook.md`
2. Architektur- und Change-Regeln in `openspec/architecture/*` und aktiven `openspec/changes/*`
3. Operative Entwicklerhinweise in `README.md` und `docs/getting-started.md`
4. Historische Snapshots (nur Kontext)

## 5. Pflegeprozess

- Bei jeder strukturellen oder sicherheitsrelevanten Aenderung muss mindestens ein
  verlinktes, verbindliches Dokument aktualisiert werden.
- PRs mit Architektur- oder Security-Impact enthalten einen Abschnitt
  "Dokumentation aktualisiert".
- Veraltete Seiten werden sichtbar als "veraltet" markiert und in den Legacy-Bereich
  verschoben.
