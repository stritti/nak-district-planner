# Roadmap und aktueller Stand

> **Stand: 11. Oktober 2026.** [v1.0.0](https://github.com/stritti/nak-district-planner/releases/tag/v1.0.0) ist seit dem 10. Oktober 2026 stabil veröffentlicht. Für kommende Features sind weder Version noch Termin verbindlich festgelegt.

Diese Seite ist die **einzige aktive produktbezogene Roadmap**. Die verbindlichen Regeln für implementiertes Verhalten stehen in der [OpenSpec-Baseline](https://github.com/stritti/nak-district-planner/tree/main/openspec/specs). [Aktive OpenSpec-Changes](https://github.com/stritti/nak-district-planner/tree/main/openspec/changes) und GitHub-Issues beschreiben Änderungen, die noch nicht notwendigerweise umgesetzt sind.

## Fachlicher Backlog

| Vorhaben | Umfang | Nachweis | Status |
| --- | --- | --- | --- |
| Wiederkehrende Gemeinde-/Bezirkstermine | Wochen-/Monatsmuster, monatliche Checkliste, explizite Übernahme, DST-/Konflikt-/Rechteprüfungen, Dubletten verhindern | [Issue #557](https://github.com/stritti/nak-district-planner/issues/557), [PR #558](https://github.com/stritti/nak-district-planner/pull/558) | **Nur OpenSpec, nicht implementiert** |
| Konfigurierbare Aufgaben je Termin | Schließdienst, Organist, Dirigent, Namensvorschläge und Amtsträger-Lifecycle | [PR #525](https://github.com/stritti/nak-district-planner/pull/525) | **Nur OpenSpec, nicht implementiert** |
| Inline-Editing in Übersichten | Berechtigte Tabellenzellen bearbeiten; gemeinsamer Vue-Editor mit Konflikt-/Fehlerbehandlung | [PR #530](https://github.com/stritti/nak-district-planner/pull/530) | **Nur OpenSpec, nicht implementiert** |

**Vorgeschlagene Reihenfolge:** zuerst wiederkehrende Termine, dann organisatorische Aufgaben, danach tabellenweites Inline-Editing. Das ist keine beschlossene Release-Zusage; Security- und Architekturabhängigkeiten können eine andere Reihenfolge erfordern.

## Technische Nacharbeiten

| Thema | Offenes Issue | Geplanter Schwerpunkt |
| --- | --- | --- |
| OIDC und Datenschutz | [#471](https://github.com/stritti/nak-district-planner/issues/471) | Opaque Token-Bindung, JWKS-Refetch, Log-/Fehlerdaten, gehashte Export-Tokens |
| Kalendersynchronisation | [#470](https://github.com/stritti/nak-district-planner/issues/470) | Fehler persistieren, nicht blockierende Locks, Valkey-Broker und Task-Limits |
| Produktivbetrieb | [#472](https://github.com/stritti/nak-district-planner/issues/472) | Container-Härtung, Healthchecks, Secret-Guards, PWA-Fallback, Restore |
| Architektur | [#474](https://github.com/stritti/nak-district-planner/issues/474) | Doppelten/toten Code reduzieren, Ports & Adapters durchsetzen |
| Berechtigungen und Serien | [#503](https://github.com/stritti/nak-district-planner/issues/503) | Rollenvertrag angleichen, Serien nach Verschiebungen nicht erneut erzeugen |

Diese Issues sind **Folgearbeiten nach v1.0** und nicht rückwirkend Blocker des veröffentlichten Releases. Aktuelle Änderungen siehe [offene Issues](https://github.com/stritti/nak-district-planner/issues?q=is%3Aissue%20is%3Aopen), [PRs](https://github.com/stritti/nak-district-planner/pulls) und [Releases](https://github.com/stritti/nak-district-planner/releases).

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
