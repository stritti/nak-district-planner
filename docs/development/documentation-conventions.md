# Konventionen für Projektdokumentation

## Ablage und Zuständigkeiten

| Typ | Ablage | Verbindlichkeit |
| --- | --- | --- |
| Projektüberblick und Einstieg | `README.md`, `docs/index.md` | Einstieg, keine duplizierten Fachregeln |
| Fachliche Fähigkeiten | `docs/features/` und `docs/guide/` | Erklärungen mit Verweis auf OpenSpec |
| Architektur/ADRs | `docs/architecture/`, `docs/architecture/decisions/` | Entscheidungsgrundlagen und Architekturüberblick |
| Entwicklung | `docs/development/` | Build, Tests, Qualitätsanforderungen |
| Betrieb | `docs/operations/` | Deployment, Monitoring, Migration, Rollback |
| Sicherheit | `docs/security/` | Sicherheitsrahmen, Betriebsgrenzen |
| Historische Analysen/Pläne | `docs/archive/` | Referenz, nicht aktueller Projektstatus |
| Implementierte Produktregeln | `openspec/specs/` | Normativer Vertrag |
| Geplante Änderungen | `openspec/changes/` | Noch nicht unbedingt implementiert |
| Abgeschlossene Änderungen | `openspec/changes/archive/` | Nachweis historischer Specs |

Die aktive **Roadmap** ist ausschließlich `docs/roadmap.md`; Arbeitstickets liegen auf GitHub. Sicherheitshinweise für Melder stehen unter `.github/SECURITY.md`, Beiträge unter `.github/CONTRIBUTING.md`.

## Dateinamen

- Gewöhnliche Markdown-Dateien: englisch, kleingeschrieben, **kebab-case**, beschreibende Substantive (z. B. `production-runbook.md`).
- Entscheidung: fortlaufende ADR-Nummer mit Titel, z. B. `0001-external-calendar-sync-trust.md`.
- GitHub-Sonderdateien behalten etablierte Namen (`README.md`, `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`).
- Deutsche Fließtexte und deutschsprachige Navigation sind erwünscht, Dateinamen und technische Links bleiben konsistent.

## Status und Verlinkung

- **Implemented**, **planned** und **historical** klar unterscheiden; nur basierend auf aktuellem Code-/GitHub-Status behaupten.
- Eine Fachregel hat genau eine maßgebliche Quelle (OpenSpec); Überblicksseiten verlinken.
- Relative Repository-Links und kanonische VitePress-Routen nutzen; externe Links nicht ohne Prüfung auf eine andere Seite richten.
- Beim Verschieben öffentlicher Dokumentationsseiten bestehende VitePress-URLs über `rewrites` in `docs/.vitepress/config.mts` stabil halten. Neue interne Links auf den kanonischen Zielort richten.
- Ein abgeschlossener OpenSpec-Change wird archiviert; historische Analysen wandern in `docs/archive/`.
- VitePress-Build (`bun run docs:build`), OpenSpec-Validierung und Referenzen prüfen, bevor ein Dokumentations-PR gemerged wird.

## Archivieren statt löschen

Historische Reviews und technische Konzepte möglichst mit Datum und Hinweis auf ihren damaligen Gültigkeitsstand erhalten. Redundante Kopien ohne eigenständigen Inhalt können entfernt werden, wenn Git-Historie beziehungsweise Archivindex die frühere Fassung nachweisbar auffindbar halten.
