---
layout: home
hero:
  name: "NAK District Planner"
  text: "Gottesdienste gemeinsam planen"
  tagline: "Eine gemeinsame Sicht auf Gemeinden, Termine und Dienstleitungen: Lücken erkennen, Dienste zuweisen und Kalender verlässlich teilen."
  actions:
    - theme: brand
      text: So funktioniert es
      link: /workflows
    - theme: alt
      text: Funktionen und Regeln
      link: /use-cases
    - theme: alt
      text: GitHub
      link: https://github.com/stritti/nak-district-planner
features:
  - title: "Gemeinsame Dienstmatrix"
    details: "Gottesdienste mehrerer Gemeinden überblicken und offene Dienstleitungen gezielt zuweisen."
    link: /workflows#dienstplanung
    linkText: Ablauf ansehen
  - title: "Kalender synchronisieren"
    details: "Vertrauenswürdige ICS- und CalDAV-Quellen anbinden und wiederholte Pflege reduzieren."
    link: /workflows#kalender-synchronisieren
    linkText: Synchronisierung verstehen
  - title: "Gemeinden verbinden"
    details: "Bezirksveranstaltungen verteilen und Einladungen zwischen Gemeinden nachvollziehbar abbilden."
    link: /invitations
    linkText: Einladungen verstehen
  - title: "Termine veröffentlichen"
    details: "Öffentliche und interne iCalendar-Abonnements mit abgestufter Datensichtbarkeit."
    link: /use-cases#uc-05-sicherer-export-ical
    linkText: Exportregeln lesen
---

## Von Einzelabsprachen zum gemeinsamen Dienstplan

Ein Bezirk koordiniert Gottesdienste und Veranstaltungen in mehreren Gemeinden. Der NAK District Planner macht sichtbar, **wann und wo ein Gottesdienst geplant ist, wer die Dienstleitung übernimmt und wo noch eine Besetzung fehlt**.

Die wichtigsten Abläufe sind unter [So funktioniert der Bezirksplaner](/workflows) beschrieben. Die [Use Cases](/use-cases) enthalten die fachlichen Details.

::: info Stand der Kalenderanbindung
Version 1 unterstützt als externe Kalenderquellen **ICS und CalDAV über HTTPS**. Google Calendar und Microsoft 365 sind für eine spätere Version vorgesehen und nicht als produktive V1-Integration freigegeben. Der [Architekturstatus](/architecture-status) unterscheidet implementierte Funktionen und Zielbild.
:::

## Der richtige Einstieg

- **Planung:** [Workflows](/workflows), [Use Cases](/use-cases) und [Rollenkonzept](/roles)
- **Entwicklung:** [Lokaler Einstieg](/getting-started), [Engineering Standards](/engineering-standards)
- **Betrieb:** [Produktiv-Stack](/production-compose), [Runbook](/production-runbook)
- **Quellen und Spezifikationen:** [Dokumentationslandkarte](/documentation-map)

Der Quellcode steht unter [AGPL-3.0-only](/licensing).
