## ADDED Requirements

### Requirement: Hilfeinhalte muessen nach Auth-Status segmentiert sein
Das System MUST unterschiedliche Hilfeinhalte fuer nicht angemeldete und angemeldete Nutzer bereitstellen.

#### Scenario: Nicht angemeldeter Nutzer sieht Gast-Hilfe
- **WHEN** ein nicht angemeldeter Nutzer einen Kontext mit Hilfeinhalt aufruft
- **THEN** zeigt das System nur Hilfeinhalte fuer nicht angemeldete Nutzer an

#### Scenario: Angemeldeter Nutzer sieht keine Gast-Hilfe
- **WHEN** ein angemeldeter Nutzer denselben Kontext aufruft
- **THEN** zeigt das System keine Hilfeinhalte an, die ausschliesslich fuer nicht angemeldete Nutzer vorgesehen sind

### Requirement: Nicht angemeldete Nutzer erhalten Registrierungsleitfaden
Das System MUST fuer nicht angemeldete Nutzer einen klaren Hilfeablauf fuer den Registrierungsprozess bereitstellen.

#### Scenario: Registrierungsprozess wird als Schritte dargestellt
- **WHEN** ein nicht angemeldeter Nutzer die registrierungsnahe Hilfe oeffnet
- **THEN** enthaelt der Hilfeinhalt mindestens die benoetigten Registrierungsschritte in nachvollziehbarer Reihenfolge

### Requirement: Angemeldete Nutzer erhalten rollenspezifische Workflows
Das System MUST fuer angemeldete Nutzer Hilfeinhalte rollenabhaengig ausspielen und dabei mindestens `viewer` und `planner` unterscheiden.

#### Scenario: Viewer erhaelt Viewer-Workflow-Hilfe
- **WHEN** ein angemeldeter Nutzer mit Rolle `viewer` einen relevanten Arbeitsbereich aufruft
- **THEN** zeigt das System Hilfeinhalte mit Viewer-Workflows und Viewer-Moeglichkeiten

#### Scenario: Planner erhaelt Planner-Workflow-Hilfe
- **WHEN** ein angemeldeter Nutzer mit Rolle `planner` einen relevanten Arbeitsbereich aufruft
- **THEN** zeigt das System Hilfeinhalte mit Planner-Workflows und Planner-Moeglichkeiten

### Requirement: Hilfeinhalte muessen rollenfremde Inhalte ausblenden
Das System MUST verhindern, dass Hilfeinhalte fuer andere Rollen als die aktuelle Nutzerrolle sichtbar sind.

#### Scenario: Viewer sieht keine Planner-spezifischen Hinweise
- **WHEN** ein Nutzer mit Rolle `viewer` einen Kontext mit verfuegbaren Planner-Hilfen aufruft
- **THEN** werden Hilfeinhalte mit Zielrolle `planner` nicht angezeigt
