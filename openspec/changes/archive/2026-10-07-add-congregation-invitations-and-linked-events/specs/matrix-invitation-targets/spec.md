## ADDED Requirements

### Requirement: Einladungsziel in Matrixzelle eines Gottesdienstes setzen
Das System SHALL es erlauben, in der Matrix pro Gottesdienstzelle ein Einladungsziel zu hinterlegen.

#### Scenario: Internes Bezirksziel aus einer Gottesdienstzelle setzen
- **WHEN** ein Benutzer eine Gottesdienstzelle oeffnet und ein Ziel vom Typ `DISTRICT_CONGREGATION` auswaehlt
- **THEN** speichert das System die Zielgemeinde als referenzierte Einladung fuer diesen Gottesdienst

#### Scenario: Externes Ziel als Freitext aus einer Gottesdienstzelle setzen
- **WHEN** ein Benutzer in einer Gottesdienstzelle ein Ziel vom Typ `EXTERNAL_NOTE` mit Freitext eintraegt
- **THEN** speichert das System den Freitext-Hinweis als Einladung fuer diesen Gottesdienst

#### Scenario: Bestehende Einladung wird im Dialog angezeigt
- **WHEN** ein Benutzer den Gottesdienst-Dialog einer bereits eingeladenen Zelle oeffnet
- **THEN** zeigt der Dialog die vorhandenen Einladungen an, damit diese bei Bedarf geaendert oder geloescht werden koennen

### Requirement: Bestehende Dienstleiter-Zuordnung in der Matrix bleibt unveraendert nutzbar
Das System SHALL die bestehende Dienstplan-Matrix-Funktion (Anzeige, LUECKE-Logik, Zuordnung von Dienstleitern) unveraendert weiter nutzbar halten, auch wenn Einladungsziele aktiviert sind.

#### Scenario: Matrix bleibt mit Einladungsziel sichtbar und bedienbar
- **WHEN** ein Bezirk eine Matrix mit gesetztem Einladungsziel aufruft
- **THEN** wird die Matrix weiterhin gerendert und die Zellen fuer Gottesdienst-Zuordnungen bleiben bedienbar

#### Scenario: Dienstleiter-Zuordnung bleibt moeglich trotz Einladungsziel
- **WHEN** ein Benutzer in einer Matrixzelle mit bestehendem oder fehlendem Assignment arbeitet und fuer die Gemeinde ein Einladungsziel hinterlegt ist
- **THEN** kann der Benutzer weiterhin wie bisher einen Dienstleiter zuweisen oder bestehende Zuordnungsinformationen sehen

### Requirement: Zieltyp-Validierung in Matrix-API
Das System SHALL bei Matrix-Einladungszielen genau einen gueltigen Zieltyp pro Eintrag akzeptieren.

#### Scenario: Ungueltige Kombination wird abgewiesen
- **WHEN** ein API-Request gleichzeitig `target_congregation_id` und `external_target_note` fuer denselben Eintrag setzt
- **THEN** lehnt das System den Request mit Validierungsfehler ab

#### Scenario: Fehlender Zielwert wird abgewiesen
- **WHEN** ein API-Request weder `target_congregation_id` noch `external_target_note` fuer ein Einladungsziel liefert
- **THEN** lehnt das System den Request mit Validierungsfehler ab

### Requirement: Einladungsziel in Matrix sichtbar machen
Das System SHALL in der Matrixansicht die Einladung in der jeweiligen Gottesdienstzelle sichtbar machen.

#### Scenario: Einladungshinweis wird in Zelle angezeigt
- **WHEN** ein Gottesdienst in einer Gemeinde eine Einladung aus einer Host-Gemeinde ist
- **THEN** zeigt die betroffene Matrixzelle den Hinweis auf die Host-Gemeinde an

#### Scenario: Host-Zelle zeigt Anzahl von Einladungen
- **WHEN** ein Host-Gottesdienst Einladungen an andere Gemeinden besitzt
- **THEN** zeigt die Host-Zelle in der Matrix einen Hinweis mit der Anzahl der Einladungen

#### Scenario: Keine Einladung im Gemeinde-Kopf
- **WHEN** die Matrix dargestellt wird
- **THEN** wird die Einladung nicht als statischer Hinweis im Gemeinde-Kopf, sondern nur kontextbezogen in der Gottesdienstzelle angezeigt
