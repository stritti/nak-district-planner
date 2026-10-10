# Design: Aufgabenzentrierte Dokumentation

## Verbindliche Informationsarchitektur

- Startseite: Nutzen und Geltungsbereich.
- Workflows: zusammenhängende fachliche Arbeitsabläufe.
- Use Cases, Rollen, Einladungen: detaillierte fachliche Regeln.
- Architekturstatus und OpenSpec: Implementierung, Ziel und Änderungen.
- Runbooks: Entwicklung und Betrieb.

Die Einstiegsseiten verlinken kanonische Fachreferenzen, statt Details zu duplizieren.

## Diagramme

Das Build-Time-Plugin `vitepress-plugin-mermaid-diagram` konvertiert gültige Mermaid-Flowcharts und Sequence-Diagramme zu statischem SVG. Der veröffentlichte Webauftritt benötigt daher weder einen zusätzlichen Mermaid-Runtime-Bundle noch einen externen Diagrammdienst. Begleitender Fließtext erklärt die Abläufe.

## Risiken

- **Capability Drift:** Explizite V1-Abgrenzung (ICS/CalDAV gegenüber geplanten Providern), Verweis auf Architekturstatus.
- **Linkbruch:** VitePress bleibt bei `ignoreDeadLinks: false`.
- **Ungültige Diagramme:** Vorhandene Mermaid-Fences korrigieren und SVG-Ausgabe in CI prüfen.
- **Dependency Drift:** Plugin-Version festhalten und Bun-Lockdatei aktualisieren.

## Qualität

VitePress-Dokumentations-Build, OpenSpec-Validierung und automatische Prüfung auf SVG-Diagramme in den erzeugten Seiten.
