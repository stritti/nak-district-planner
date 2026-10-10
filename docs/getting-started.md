# Lokaler Einstieg für Entwickler

Die fachlichen Abläufe stehen unter [So funktioniert der Bezirksplaner](/workflows). Diese Seite behandelt nur die **lokale Dokumentation**. Die Anwendung selbst wird im [Repository-README](https://github.com/stritti/nak-district-planner#entwicklung) eingerichtet.

## VitePress starten

Im Repository-Root mit Bun:

```bash
bun install --frozen-lockfile
bun run docs:dev
```

VitePress meldet die lokale Adresse, üblicherweise `http://localhost:5173`.

## Dokumentation bauen und Links prüfen

```bash
bun run docs:build
```

Die statische Website wird nach `docs/.vitepress/dist` geschrieben. Der Build prüft interne Links und rendert Mermaid-Diagramme als SVG.

## Weiterführende Quellen

- Fachliche Regeln: [Use Cases](/use-cases), [Rollen](/roles)
- Implementierung: [Architekturstatus](/architecture-status), [Engineering Standards](/engineering-standards)
- Betrieb: [Production Runbook](/production-runbook), [Security Baseline](/security-baseline)
- Spezifikationen und Dokumentstatus: [Dokumentationslandkarte](/documentation-map)

Verhaltensänderungen werden über OpenSpec spezifiziert; Einstiegstexte ersetzen keine normativen Anforderungen.
