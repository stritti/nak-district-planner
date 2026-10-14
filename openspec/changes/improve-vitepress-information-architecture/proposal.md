# Proposal: Nutzerorientierte VitePress-Dokumentation

## Why

Die Startseite präsentiert vor allem Technik statt Mehrwert. Die Navigation mischt Referenzen mit Nutzeraufgaben. Wiederholungen und ungültige Mermaid-Fences erschweren den Einstieg.

## What Changes

- Mehrwert, V1-Funktionsumfang und Grenzen prominent auf der Startseite zeigen.
- End-to-End-Workflow für Matrixplanung, Kalender, Einladungen, Export und Freigabe einführen.
- Navigation nach Nutzeraufgaben und Dokumentationslandkarte nach Verbindlichkeit strukturieren.
- Verbindliche, nach Themen gegliederte Routen unter `/guide/`, `/features/`, `/architecture/`, `/development/`, `/operations/`, `/security/` und `/archive/`; keine Rewrite-Aliasse für alte URLs.
- Historische Roadmaps und RC-Reviews im Archiv bündeln; VitePress, GitHub-Repository-Verweise, Verifikation und REUSE-Metadaten auf die neue Struktur abstimmen.
- Redundante Ausführungen durch Links auf Detailreferenzen ersetzen.
- Mermaid-Flowcharts und Sequenzen als statische SVG im Build rendern.

## Non-goals

- Keine Änderung an Produktverhalten, Datenmodell oder APIs.
- Keine produktive Freigabe von Google Calendar oder Microsoft 365.
- Keine fachliche Neuschreibung historischer Architektur- und Betriebsberichte; Archivierung und eindeutige Statushinweise sind Teil der Informationsarchitektur.

## Validation

VitePress-Build mit Dead-Link-Prüfung, OpenSpec-Validierung sowie SVG- und Navigationsprüfung.
