## ADDED Requirements

### Requirement: Kontextuelle Hilfe muss am Nutzungskontext ausgerichtet sein
Das System MUST Hilfe-Module direkt in den relevanten UI-Kontexten anzeigen, sodass Nutzer Unterstuetzung am Point of Need erhalten, ohne den aktuellen Workflow verlassen zu muessen.

#### Scenario: Hilfe in relevanter View sichtbar
- **WHEN** ein Nutzer eine View mit zugeordnetem Hilfe-Kontext oeffnet
- **THEN** zeigt das System mindestens ein passendes Hilfe-Modul in dieser View an

#### Scenario: Hilfe blockiert den Workflow nicht
- **WHEN** ein Hilfe-Modul in einer View dargestellt wird
- **THEN** bleiben primaere Aktionen der View ohne modalen Zwang weiterhin direkt ausfuehrbar

### Requirement: Hilfe muss pro Modul ausblendbar sein
Das System MUST pro Hilfe-Modul eine sichtbare Aktion zum Ausblenden bereitstellen und den ausgeblendeten Zustand pro Nutzerkontext und Hilfe-ID speichern.

#### Scenario: Angemeldeter Nutzer blendet Hilfe aus
- **WHEN** ein angemeldeter Nutzer ein Hilfe-Modul mit einer gueltigen Hilfe-ID ausblendet
- **THEN** zeigt das System dieses Hilfe-Modul bei spaeteren Sitzungen desselben Nutzers standardmaessig nicht mehr an

#### Scenario: Nicht angemeldeter Nutzer blendet Hilfe aus
- **WHEN** ein nicht angemeldeter Nutzer ein Hilfe-Modul ausblendet
- **THEN** bleibt das Hilfe-Modul im selben Browser fuer den gespeicherten lokalen Zustand ausgeblendet

### Requirement: Ausgeblendete Hilfe muss wieder eingeblendet werden koennen
Das System MUST eine auffindbare Aktion bereitstellen, mit der Nutzer zuvor ausgeblendete Hilfe-Module wieder einblenden koennen.

#### Scenario: Nutzer reaktiviert ausgeblendete Hilfe
- **WHEN** ein Nutzer die Aktion zum Wiederherstellen der Hilfe ausfuehrt
- **THEN** zeigt das System alle fuer Rolle und Kontext passenden Hilfe-Module wieder an
