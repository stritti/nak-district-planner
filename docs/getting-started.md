# Erste Schritte

Diese Anleitung hilft Ihnen beim Einstieg in die Projekt-Dokumentation.

## Installation

Um die Dokumentation lokal zu starten, müssen Sie die Abhängigkeiten installieren:

```bash
npm install
```

## Lokale Entwicklung

Starten Sie den Entwicklungs-Server mit folgendem Befehl:

```bash
npm run docs:dev
```

Die Dokumentation ist dann unter `http://localhost:5173` (oder dem nächsten freien Port) erreichbar.

## Dokumentation bauen

Um die Dokumentation für das Produktiveinsatz zu bauen:

```bash
npm run docs:build
```

Die erzeugten Dateien befinden sich im Ordner `docs/.vitepress/dist`.
