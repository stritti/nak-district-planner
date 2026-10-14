## ADDED Requirements

### Requirement: Einladung zwischen Gemeinden anlegen
Das System SHALL es erlauben, eine Einladung von einer Einladungs-Gemeinde an eine oder mehrere Zielgemeinden anzulegen, sodass der Termin in allen beteiligten Gemeinden sichtbar wird.

#### Scenario: Einladung an Bezirks-Gemeinde anlegen
- **WHEN** ein Benutzer fuer einen bestehenden Termin eine Einladung mit einem Ziel vom Typ `DISTRICT_CONGREGATION` erstellt
- **THEN** wird eine Einladungsbeziehung gespeichert und der Termin in der eingeladenen Gemeinde als Einladungstermin sichtbar

#### Scenario: Mehrere Zielgemeinden in einer Einladung
- **WHEN** ein Benutzer bei der Einladung mehrere Zielgemeinden angibt
- **THEN** erzeugt das System fuer jede Zielgemeinde eine eigene verknuepfte Einladungskonfiguration

### Requirement: Einladungshinweis in eingeladenen Gemeinden anzeigen
Das System SHALL bei Einladungsterminen in eingeladenen Gemeinden die Einladungs-Gemeinde eindeutig anzeigen.

#### Scenario: Eventliste zeigt Einladungsquelle
- **WHEN** eine eingeladene Gemeinde ihre Eventliste abruft und ein Einladungstermin enthalten ist
- **THEN** enthaelt der Eventdatensatz einen Hinweis auf die Einladungs-Gemeinde

#### Scenario: Eventdetail zeigt Einladungsquelle
- **WHEN** ein Benutzer den Einladungstermin in der Detailansicht oeffnet
- **THEN** zeigt die Ansicht den Namen der Einladungs-Gemeinde als Herkunftshinweis

### Requirement: Freitext-Einladung ausserhalb des Bezirks erfassen
Das System SHALL Einladungsziele ausserhalb des Bezirks als Freitext-Hinweis speichern koennen.

#### Scenario: Externes Ziel als Freitext anlegen
- **WHEN** ein Benutzer ein Ziel vom Typ `EXTERNAL_NOTE` mit einem Freitext angibt
- **THEN** speichert das System den Freitext-Hinweis als Einladungsziel ohne `target_congregation_id`

#### Scenario: Freitext in Einladung anzeigen
- **WHEN** ein Einladungseintrag mit externem Freitext-Ziel abgerufen wird
- **THEN** liefert die API den Freitext-Hinweis unveraendert zur Anzeige aus
