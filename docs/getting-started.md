# Erste Schritte

Diese Anleitung hilft beim schnellen Einstieg in Entwicklung und Dokumentation.

## Quelle der Wahrheit

Starten Sie mit der Dokumentationslandkarte: [`documentation-map.md`](./documentation-map.md).
Dort ist definiert, welche Dokumente verbindlich, geplant oder historisch sind.

## Installation

Im Projekt wird fuer JavaScript-Tooling standardmaessig **bun** verwendet.
Installieren Sie die Abhaengigkeiten im Repository-Root:

```bash
bun install
```

## Lokale Entwicklung

Starten Sie den Entwicklungs-Server mit folgendem Befehl:

```bash
bun run docs:dev
```

Die Dokumentation ist dann unter `http://localhost:5173` (oder dem nächsten freien Port) erreichbar.

## Dokumentation bauen

Um die Dokumentation fuer den Produktiveinsatz zu bauen:

```bash
bun run docs:build
```

Die erzeugten Dateien befinden sich im Ordner `docs/.vitepress/dist`.

## Inhaltlicher Einstieg

Empfohlene Reihenfolge fuer neue Entwickler:

1. `README.md` (Setup, Laufzeit, Deployment-Basis)
2. `docs/documentation-map.md` (Dokumentstatus)
3. `openspec/architecture/overview.md` (Zielarchitektur)
4. `docs/use-cases.md` und `docs/roles.md` (fachliche Regeln)
