# Design: Aufgabenzentrierte Dokumentation

## Verbindliche Informationsarchitektur

- Startseite: Nutzen und Geltungsbereich.
- Workflows: zusammenhängende fachliche Arbeitsabläufe.
- Use Cases, Rollen, Einladungen: detaillierte fachliche Regeln.
- Architekturstatus und OpenSpec: Implementierung, Ziel und Änderungen.
- Runbooks: Entwicklung und Betrieb.

Die Einstiegsseiten verlinken kanonische Fachreferenzen, statt Details zu duplizieren.

### Kanonische Ablage und URLs

| Bereich | URL-Präfix | Dokumentationsquelle |
| --- | --- | --- |
| Leitfäden | `/guide/` | `docs/guide/` |
| Fachliche Funktionen | `/features/` | `docs/features/` |
| Architektur und ADR | `/architecture/` | `docs/architecture/` |
| Entwicklung | `/development/` | `docs/development/` |
| Betrieb | `/operations/` | `docs/operations/` |
| Sicherheit | `/security/` | `docs/security/` |
| Historie | `/archive/` | `docs/archive/` |

Die URL folgt unmittelbar dem VitePress-Quellpfad, ohne `rewrites` für die ehemals flache Dokumentation. Navigation, Querverweise und Dokumentations-HTML-Tests verwenden ausschließlich die neuen kanonischen Pfade. Damit akzeptiert die Migration bewusst geänderte bestehende Links.

Die OpenSpec-Baseline und aktiven Changes bleiben in `openspec/specs/` beziehungsweise `openspec/changes/`. Alte Architektursequenzen und Security-Roadmaps außerhalb dieser normativen Pfade wandern ins historische Dokumentationsarchiv.


## Diagramme

Das Build-Time-Plugin `vitepress-plugin-mermaid-diagram` konvertiert gültige Mermaid-Flowcharts und Sequence-Diagramme zu statischem SVG. Der veröffentlichte Webauftritt benötigt daher weder einen zusätzlichen Mermaid-Runtime-Bundle noch einen externen Diagrammdienst. Begleitender Fließtext erklärt die Abläufe.

## Risiken

- **Capability Drift:** Explizite V1-Abgrenzung (ICS/CalDAV gegenüber geplanten Providern), Verweis auf Architekturstatus.
- **Linkbruch:** VitePress bleibt bei `ignoreDeadLinks: false`; nach dem Entfernen der alten Routen werden Links explizit auf die kanonische Hierarchie umgestellt.
- **Ungültige Diagramme:** Vorhandene Mermaid-Fences korrigieren und SVG-Ausgabe in CI prüfen.
- **Dependency Drift:** Plugin-Version festhalten und Bun-Lockdatei aktualisieren.

## Qualität

VitePress-Dokumentations-Build, OpenSpec-Validierung und automatische Prüfung auf SVG-Diagramme in den erzeugten Seiten.
