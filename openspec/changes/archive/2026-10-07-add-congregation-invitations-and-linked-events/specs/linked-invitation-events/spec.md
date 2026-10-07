## ADDED Requirements

### Requirement: Verknuepfte Termine fuer eingeladene Gemeinden
Das System SHALL fuer jede interne Einladung einen verknuepften Termineintrag erstellen, der auf den Originaltermin der Einladungs-Gemeinde referenziert.

#### Scenario: Verknuepfter Termineintrag wird erstellt
- **WHEN** eine Einladung an eine Bezirks-Gemeinde erfolgreich angelegt wird
- **THEN** erstellt das System einen Ziel-Termineintrag mit Referenz auf den Originaltermin

#### Scenario: Verknuepfter Termineintrag ist je Gemeinde isoliert
- **WHEN** zwei unterschiedliche Gemeinden zum selben Originaltermin eingeladen sind
- **THEN** besitzt jede Gemeinde einen eigenen verknuepften Termineintrag mit eigener ID

### Requirement: Einladungen sind pro Gottesdienst eindeutig und im Dialog pflegbar
Das System SHALL pro Gottesdienst keine doppelten Einladungen fuer dasselbe Ziel anlegen und bestehende Einladungen im Dialog anzeigen, aendern und loeschen koennen.

#### Scenario: Gleiche Zielgemeinde wird nicht doppelt angelegt
- **WHEN** eine Einladung fuer denselben Gottesdienst und dieselbe Zielgemeinde erneut gespeichert wird
- **THEN** aktualisiert das System den bestehenden Eintrag statt einen doppelten Eintrag anzulegen

#### Scenario: Externe Einladung wird aktualisiert statt dupliziert
- **WHEN** eine externe Freitext-Einladung fuer denselben Gottesdienst erneut gespeichert wird
- **THEN** aktualisiert das System den vorhandenen externen Einladungseintrag

#### Scenario: Einladung im Dialog loeschen
- **WHEN** ein Benutzer im Gottesdienst-Dialog eine bestehende Einladung loescht
- **THEN** entfernt das System die Einladung und zeigt sie nicht mehr in Matrix/Dialog an

### Requirement: Dienstleiterpflege erfolgt bei Einladung nur in der Host-Gemeinde
Das System SHALL die Dienstleiter-Zuordnung fuer eingeladene Gottesdienste ausschliesslich am Host-Gottesdienst pflegen und in eingeladenen Gemeinden nur als Anzeige spiegeln.

#### Scenario: Zugewiesener Dienstleiter wird in eingeladener Gemeinde angezeigt
- **WHEN** ein Host-Gottesdienst einen Dienstleiter zugewiesen bekommt und als Einladung in eine andere Gemeinde gespiegelt ist
- **THEN** zeigt die Matrix der eingeladenen Gemeinde den zugewiesenen Dienstleiter an

#### Scenario: Eingeladene Gemeinde kann Dienstleiter nicht lokal aendern
- **WHEN** ein Benutzer in der eingeladenen Gemeinde die Matrixzelle eines Einladungsgottesdienstes oeffnet
- **THEN** bietet das System keine lokale Bearbeitung der Dienstleiter-Zuordnung an und verweist auf die Host-Gemeinde

### Requirement: Aenderungsuebernahme mit Rueckfrage
Das System SHALL bei Aenderungen am Originaltermin eine Ueberschreibungsanfrage fuer verknuepfte Zieltermine erzeugen und erst nach Bestaetigung anwenden.

#### Scenario: Pending-Overwrite nach Quellaenderung
- **WHEN** ein Benutzer in der Einladungs-Gemeinde Datum, Uhrzeit, Ort oder Beschreibung des Originaltermins aendert
- **THEN** markiert das System die verknuepften Zieltermine als `PENDING_OVERWRITE` mit den vorgeschlagenen neuen Werten

#### Scenario: Bestaetigte Ueberschreibung wird angewendet
- **WHEN** eine eingeladene Gemeinde die Ueberschreibungsanfrage bestaetigt
- **THEN** uebernimmt das System die vorgeschlagenen Werte in den verknuepften Zieltermin und markiert die Anfrage als abgeschlossen

#### Scenario: Abgelehnte Ueberschreibung bleibt lokal bestehen
- **WHEN** eine eingeladene Gemeinde die Ueberschreibungsanfrage ablehnt
- **THEN** behaelt der Zieltermin seine bisherigen lokalen Werte und die Anfrage wird als abgelehnt protokolliert

### Requirement: API fuer Ueberschreibungsentscheidungen
Das System SHALL einen API-Mechanismus bereitstellen, mit dem eingeladene Gemeinden offene Ueberschreibungsanfragen auflisten und bestaetigen oder ablehnen koennen.

#### Scenario: Offene Anfragen abrufen
- **WHEN** eine eingeladene Gemeinde offene Ueberschreibungsanfragen abfragt
- **THEN** gibt die API alle offenen Anfragen mit Original- und vorgeschlagenen Werten zurueck

#### Scenario: Entscheidung speichern
- **WHEN** eine eingeladene Gemeinde eine Anfrage mit `ACCEPTED` oder `REJECTED` beantwortet
- **THEN** speichert das System die Entscheidung revisionssicher mit Zeitstempel
