## ADDED Requirements

### Requirement: Authentifizierte Benutzer können ihr lokales Anzeigeprofil verwalten

Der Dienst SHALL jedem authentifizierten OIDC-Subject, einschließlich Benutzern mit `PENDING_APPROVAL`, eine geschützte Self-Service-Ansicht und die Endpunkte `GET /api/v1/profile/me` sowie `PUT /api/v1/profile/me` bereitstellen. Der Dienst SHALL `given_name_override` und `family_name_override` unabhängig von den per OIDC aktualisierten `users`-Stammdaten speichern. Die effektiven Namen SHALL die lokale Überschreibung vor den aktuellen Provider-Werten bevorzugen. `PUT` SHALL beide Override-Felder enthalten und die effektive Profilantwort liefern.

#### Scenario: Neuer Benutzer ohne Überschreibungen
- **WHEN** der authentifizierte Benutzer erstmals das eigene Profil öffnet
- **THEN** zeigt der Dienst den aktuellen IdP-Namen, die E-Mail und die Anmeldekennung
- **AND** beide Override-Felder sind `null`
- **AND** es wird keine Keycloak-spezifische API verwendet

#### Scenario: Eigene lokale Namensänderung
- **WHEN** der Benutzer `{"given_name_override":"Max","family_name_override":"Beispiel"}` speichert
- **THEN** antwortet die API mit den effektiven Werten „Max“ und „Beispiel“
- **AND** diese Werte bleiben nach Reload und erneuter Anmeldung bestehen
- **AND** die `users`-OIDC-Claims bleiben unverändert

#### Scenario: Zurücksetzen auf Provider-Werte
- **WHEN** der Benutzer beide Overrides explizit auf `null` setzt
- **THEN** werden die lokalen Namensüberschreibungen aufgehoben
- **AND** die aktuellen IdP-Werte werden wieder dargestellt

#### Scenario: Einseitige Überschreibung und fehlende Claims
- **WHEN** nur ein Override gesetzt ist oder der IdP nur Teile des Namens liefert
- **THEN** verwendet der Dienst für jeden Teil separat Override oder Provider-Fallback
- **AND** fehlende Angaben werden sicher als fehlend behandelt, ohne eine erfundene Identität abzuleiten

### Requirement: Self-Service-Profil SHALL Identität und Rollen schützen

Der Dienst MUST das Zielprofil ausschließlich aus dem serverseitig validierten OIDC-Subject bestimmen und MUST alle mutierenden Requests auf die zwei zulässigen Anzeige-Felder beschränken. E-Mail, Benutzername, OIDC-Subject, Verifikationsstatus, Passwort, Superadmin-Status, Mitgliedschaften und Genehmigungen SHALL durch Profiländerungen unberührt bleiben. Die Profildatenbank SHALL die eigenen Datensätze über RLS und serverseitige Rechte gegen fremden Zugriff isolieren.

#### Scenario: Fehlende Authentifizierung
- **WHEN** ein anonymer Client das Profil liest oder schreibt
- **THEN** antwortet der Dienst mit `401 Unauthorized`
- **AND** keine Profildaten werden preisgegeben oder geändert

#### Scenario: Fremder Subject oder verbotene Felder
- **WHEN** ein Benutzer `user_sub`, `is_superadmin`, `email`, `role` oder andere nicht freigegebene Felder im Schreib-Payload übermittelt
- **THEN** antwortet der Dienst mit `422 Unprocessable Entity`
- **AND** weder das eigene noch ein fremdes Identitäts- oder Berechtigungsfeld wird verändert

#### Scenario: RLS verweigert Zugriff auf fremdes Profil
- **WHEN** der DB-Kontext auf Subject A gesetzt ist und A versucht, Overrides von B direkt auszulesen, zu ändern oder anzulegen
- **THEN** verhindern SELECT-/UPDATE-/INSERT-/DELETE-Regeln den Fremdzugriff
- **AND** ein fehlender DB-Subject-Kontext gewährt keinen Profilzugriff

#### Scenario: Konto noch nicht freigeschaltet
- **WHEN** ein angemeldetes Konto `PENDING_APPROVAL` hat
- **THEN** ist die Bearbeitung des eigenen Anzeigeprofils möglich
- **AND** daraus folgen keine neuen fachlichen Berechtigungen

### Requirement: Profilvalidierung und Fehlerbehandlung

`PUT /api/v1/profile/me` SHALL ausschließlich zwei Pflichtfelder `given_name_override` und `family_name_override` akzeptieren, jeweils als `null` oder nach Trim nicht leerer Zeichenfolge mit maximal 100 Unicode-Zeichen. Ungültige Eingaben SHALL `422` ergeben und die vorhandenen Werte atomar unverändert lassen. Persistenzfehler SHALL nicht als erfolgreich gespeichert dargestellt werden.

#### Scenario: Leere oder zu lange Namen
- **WHEN** ein Override aus Whitespace besteht, Kontrollzeichen enthält oder die Zeichenbegrenzung überschreitet
- **THEN** antwortet die API mit `422`
- **AND** kein Teil der bisherigen Profilwerte wird überschrieben

#### Scenario: Datenbankfehler während des Speicherns
- **WHEN** das Speichern teilweise fehlschlägt
- **THEN** erfolgt ein Rollback der gesamten Aktualisierung
- **AND** die UI meldet einen Fehler statt eines erfolgreichen Speicherns

### Requirement: Identitätsverwaltung verbleibt beim OIDC-Provider

Die Anwendung SHALL Änderungen an E-Mail, Anmeldekennung und Passwort nicht als lokale Kontobearbeitung anbieten. Eine explizit konfigurierte sichere URL zur externen Kontoverwaltung MAY zusätzlich angezeigt werden, ohne Token oder Secrets in die URL aufzunehmen. Die Anwendung MUST keine automatische Keycloak-Synchronisation zur Speicherung des Anzeigeprofils benötigen.

#### Scenario: E-Mail oder Passwort ändern
- **WHEN** der Benutzer seine E-Mail oder sein Passwort ändern möchte
- **THEN** bietet die SPA dafür keine lokale Schreiboperation an
- **AND** bei konfiguriertem Provider-Konto-Link kann er zur externen Kontoverwaltung wechseln

#### Scenario: Provider ändert den Namen nach lokalem Override
- **WHEN** IdP-Namensclaims sich bei einer späteren Anmeldung ändern, aber ein lokaler Override besteht
- **THEN** bleibt der lokale Override effektiv, bis er zurückgesetzt wird
- **AND** `sub` und Berechtigungsentscheidungen werden weiterhin allein aus authentifizierter Identität und Backend-Regeln abgeleitet

#### Scenario: Kein Konto-Link konfiguriert
- **WHEN** der Betreiber keine verifizierte Konto-Verwaltungs-URL konfiguriert hat
- **THEN** wird kein externer Link angezeigt
- **AND** die lokale Profilbearbeitung bleibt verfügbar
