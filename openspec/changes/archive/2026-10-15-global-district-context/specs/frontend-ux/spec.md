## ADDED Requirements

### Requirement: Globaler Bezirkskontext in der Navigation

Die Anwendung SHALL bei authentifizierten Benutzern auf jeder geschützten Ansicht den Namen des aktuell zugänglichen Bezirks in der Hauptnavigation anzeigen. Die Bezirksauswahl SHALL nur dann interaktiv sein, wenn die vom Backend für den aktuellen Benutzer freigegebene Bezirksliste mehr als einen Eintrag enthält. Matrix und Ereignisliste SHALL keinen eigenen Bezirksfilter anbieten und SHALL den globalen Kontext für ihre Datenabfragen verwenden.

#### Scenario: Genau ein zugänglicher Bezirk
- **WHEN** ein angemeldeter Benutzer genau einen zugänglichen Bezirk hat
- **THEN** erscheint dessen Name in der Hauptnavigation
- **AND** es gibt keine interaktive Bezirksumschaltung in Navigation, Matrix oder Ereignisliste

#### Scenario: Mehrere zugängliche Bezirke
- **WHEN** ein angemeldeter Benutzer mehrere zugängliche Bezirke hat
- **THEN** ist die aktuelle Bezirksauswahl in der globalen Navigation beschriftet und bedienbar
- **AND** nur diese zugänglichen Bezirke sind auswählbar
- **AND** der aktive Bezirk ist in jeder geschützten Ansicht erkennbar
- **AND** Matrix sowie Ereignisliste laden nach einem Wechsel Daten für den neu ausgewählten Bezirk

#### Scenario: Kein zugänglicher Bezirk
- **WHEN** ein angemeldeter Benutzer noch nicht freigeschaltet ist oder keine zugänglichen Bezirke hat
- **THEN** zeigt die Navigation keine Bezirksumschaltung
- **AND** es wird kein fremder Bezirk als aktueller Kontext verwendet

#### Scenario: Bezirksfreigabe entfällt
- **WHEN** die gespeichert ausgewählte Bezirks-ID nicht mehr in der zugänglichen Liste enthalten ist
- **THEN** wird ein gültiger Bezirk ausgewählt oder die Auswahl geleert, wenn die Liste leer ist
- **AND** eine unzulässige Auswahl kann nicht über den globalen Umschalter gesetzt werden

#### Scenario: Benutzerwechsel, Logout und verzögerte Antworten
- **WHEN** sich die Identität ändert, der Benutzer abmeldet oder eine ältere Bezirksabfrage erst nach dem Identitätswechsel antwortet
- **THEN** werden fremde Bezirksdaten und Auswahlwerte nicht übernommen
- **AND** die neue Identität beginnt mit ihrem eigenen berechtigten Bezirkskontext

#### Scenario: API-Abfrage der Bezirke schlägt fehl
- **WHEN** der Abruf der zugänglichen Bezirke fehlschlägt
- **THEN** wird kein zuvor gespeicherter Bezirk als weiterhin autorisiert ausgegeben

#### Scenario: Filter je Bezirkskontext
- **WHEN** der Benutzer den Bezirk global wechselt und anschließend zurückkehrt
- **THEN** werden gültige Matrix- und Ereignisfilter jeweils für den zugehörigen Bezirk wiederhergestellt
- **AND** ein Bezirkswechsel verändert die serverseitigen Rollen und Berechtigungsgrenzen nicht
