# Roadmap und aktueller Stand

> **Stand: 13. Oktober 2026 (GitHub-PR-Status abgeglichen).** [v1.0.0](https://github.com/stritti/nak-district-planner/releases/tag/v1.0.0) ist seit dem 10. Oktober 2026 stabil veröffentlicht. Für kommende Features sind weder Version noch Termin verbindlich festgelegt.

Diese Seite ist die **einzige aktive produktbezogene Roadmap**. Die verbindlichen Regeln für implementiertes Verhalten stehen in der [OpenSpec-Baseline](https://github.com/stritti/nak-district-planner/tree/main/openspec/specs). [Aktive OpenSpec-Changes](https://github.com/stritti/nak-district-planner/tree/main/openspec/changes) und GitHub-Issues beschreiben Änderungen, die noch nicht notwendigerweise umgesetzt sind.

## Release- und Integrationsstand

- **Veröffentlicht:** v1.0.0 (10. Oktober 2026).
- **In `main` integriert, aber nicht automatisch als veröffentlicht zu betrachten:** PR #568 (Kalendersynchronisation), #571 (Rollenvertrag/verschobene Serien) und #573 (technische Konsolidierung).
- **Release 1.0.1:** [PR #572](https://github.com/stritti/nak-district-planner/pull/572) offen; ein Release-PR ist noch keine veröffentlichte Version.
- **Implementiert, noch nicht integriert:** [Draft-PR #570](https://github.com/stritti/nak-district-planner/pull/570) (Recurring Events); aktuelle Head-SHA `b74d8ae2a8a01785c8a8fb5488088ad6ae4f3e1e`. OpenSpec-Aufgaben, fachliche Abnahme und CI auf dem finalen Head sind vor Merge zu bestätigen.
- **Produktionshärtung:** [PR #574](https://github.com/stritti/nak-district-planner/pull/574) offen; externer GitGuardian-Befund noch zu klassifizieren, ohne das Security-Gate abzuschwächen.

## Fachlicher Backlog

| Vorhaben | Umfang | Nachweis | Status |
| --- | --- | --- | --- |
| Wiederkehrende Gemeinde-/Bezirkstermine | Wochen-/Monatsmuster, monatliche Checkliste, explizite Übernahme, DST-/Konflikt-/Rechteprüfungen, Dubletten verhindern | [Issue #557](https://github.com/stritti/nak-district-planner/issues/557), [PR #558](https://github.com/stritti/nak-district-planner/pull/558) | **Implementierung in [Draft-PR #570](https://github.com/stritti/nak-district-planner/pull/570); noch nicht in `main`, fachliche Abnahme offen** |
| Konfigurierbare Aufgaben je Termin | Schließdienst, Organist, Dirigent, Namensvorschläge und Amtsträger-Lifecycle | [PR #525](https://github.com/stritti/nak-district-planner/pull/525) | **OpenSpec in `main` (PR #525); Feature-Implementierung weiterhin ausstehend** |
| Inline-Editing in Übersichten | Berechtigte Tabellenzellen bearbeiten; gemeinsamer Vue-Editor mit Konflikt-/Fehlerbehandlung | [PR #530](https://github.com/stritti/nak-district-planner/pull/530) | **OpenSpec in `main` (PR #530); Feature-Implementierung weiterhin ausstehend** |

**Vorgeschlagene Reihenfolge:** zuerst wiederkehrende Termine, dann organisatorische Aufgaben, danach tabellenweites Inline-Editing. Das ist keine beschlossene Release-Zusage; Security- und Architekturabhängigkeiten können eine andere Reihenfolge erfordern.

## Technische Nacharbeiten

| Thema | Offenes Issue | Geplanter Schwerpunkt |
| --- | --- | --- |
| OIDC und Datenschutz | [#471](https://github.com/stritti/nak-district-planner/issues/471) | Opaque Token-Bindung, JWKS-Refetch, Log-/Fehlerdaten, gehashte Export-Tokens |
| Kalendersynchronisation | [#470](https://github.com/stritti/nak-district-planner/issues/470) | **In `main` integriert:** PR #568 gemergt; Betriebs-/Release-Verifikation separat |
| Produktivbetrieb | [#472](https://github.com/stritti/nak-district-planner/issues/472) | **PR #574 offen:** Implementierung und Tests vorhanden; GitGuardian-Incident 36714356 extern zu klären |
| Architektur | [#474](https://github.com/stritti/nak-district-planner/issues/474) | **In `main` integriert:** PR #573 am 13. Oktober gemergt; Codecov-Upload benötigt weiterhin `CODECOV_TOKEN` |
| Berechtigungen und Serien | [#503](https://github.com/stritti/nak-district-planner/issues/503) | **In `main` integriert:** PR #571 gemergt; Regressionen für verschobene Serien ergänzt |

Die oben genannten Issues enthalten sowohl bereits in `main` integrierte Arbeiten als auch noch offene Folgearbeiten. Integration in `main` bedeutet nicht automatisch Veröffentlichung. Diese Themen sind **Folgearbeiten nach v1.0** und nicht rückwirkend Blocker des veröffentlichten Releases. Aktuelle Änderungen siehe [offene Issues](https://github.com/stritti/nak-district-planner/issues?q=is%3Aissue%20is%3Aopen), [PRs](https://github.com/stritti/nak-district-planner/pulls) und [Releases](https://github.com/stritti/nak-district-planner/releases).

## Release-Regeln

1. OpenSpec-Change vor einer fachlichen Verhaltensänderung erstellen und mit der bestehenden Baseline abgleichen.
2. Implementierung mit Domain-/Application-/Adapter-Grenzen, RBAC, Tenant-Isolation und migrationssicherem Datenmodell.
3. Unit-, Integrations- und gezielte **Negativ-/Ausnahme-Tests**. Verbindliche Messung siehe [Coverage-Strategie](/development/coverage-strategy), Gate nicht abschwächen.
4. CI, Security-Scans, Docs-Build und [Release-Prozess](/operations/release-process) prüfen.
5. Erst nach Implementierung und Tests die Baseline aktualisieren und den OpenSpec-Change archivieren. Ein Spec-PR allein liefert keine Funktion aus.

## Maßgebliche Dokumente

- **Fachliches Verhalten:** [OpenSpec-Baseline](https://github.com/stritti/nak-district-planner/tree/main/openspec/specs), [Use Cases](/features/use-cases)
- **Architektur:** [Architekturstatus](/architecture/status), [Engineering Standards](/development/engineering-standards)
- **Betrieb:** [Runbook](/operations/production-runbook), [Produktiv-Stack](/operations/production-compose)
- **Security:** [Security Baseline](/security/baseline)
- **Historie:** [Archivübersicht](/archive/), [Dokumentationslandkarte](/documentation-map)
