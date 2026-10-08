## Why

Die Plattform benoetigt eine kontextnahe Hilfe, damit neue und bestehende Nutzer schnell verstehen, welche Schritte sie je nach Rolle ausfuehren koennen. Aktuell fehlt eine integrierte, rollenabhaengige Orientierung direkt in den relevanten Arbeitsbereichen, was Einarbeitung und effiziente Nutzung erschwert.

## What Changes

- Fuehrt eine integrierte Hilfe-Sektion ein, die in der Anwendung an relevanten Stellen sichtbar ist, ohne den Arbeitsfluss zu stoeren.
- Zeigt unterschiedliche Hilfe-Inhalte fuer nicht angemeldete Nutzer und angemeldete Nutzer.
- Bildet fuer nicht angemeldete Nutzer den Registrierungsprozess als gefuehrten Hilfeinhalt ab.
- Stellt fuer angemeldete Nutzer rollenspezifische Inhalte fuer `viewer` und `planner` bereit (Workflows, Moeglichkeiten, typische Schritte).
- Ermoeglicht pro Hilfe-Modul ein lokales Ausblenden/Einblenden, sodass erfahrene Nutzer Hinweise reduzieren koennen.
- Definiert Sichtbarkeitsregeln und Platzierungsmuster, damit Hilfe dort verfuegbar ist, wo sie benoetigt wird (z. B. in Ansichten fuer Event-Liste, Matrix-Planung, Registrierung/Login-Kontext).

## Capabilities

### New Capabilities
- `contextual-help`: Integrierte, rollensensitive Hilfe-Komponenten mit unaufdringlicher Sichtbarkeit und Toggle zum Ausblenden.
- `role-based-help-content`: Struktur und Auslieferung von Hilfeinhalten fuer Gast, Viewer und Planner inklusive Registrierungsleitfaden und Workflow-Hinweisen.

### Modified Capabilities
- Keine.

## Impact

- Frontend: Neue UI-Komponenten/Patterns fuer Hilfe-Hinweise, rollenabhaengiges Rendering, Persistenz fuer ausgeblendete Hilfen.
- Frontend-Views: Anpassungen in Bereichen mit hohem Orientierungsbedarf (Onboarding, Event-Ansichten, Matrix-Planung).
- API/Auth-Kontext: Nutzung vorhandener Rolleninformationen fuer zielgruppengerechte Hilfeausspielung.
- Dokumentation/UX: Konsistente Inhaltsstruktur fuer Hilfe-Texte und klare Platzierungsregeln.
