## ADDED Requirements

### Requirement: Benutzeravatar und Profilmenü in der Hauptnavigation

Die SPA SHALL bei authentifizierten Benutzern rechts oben einen kreisrunden, generischen Avatar statt eines breiten Namens-/E-Mail-Blocks anzeigen. Der Avatar SHALL ohne eigene oder externe Bilddateien aus den Initialen des effektiven Vornamens und Nachnamens berechnet werden. Das Avatar-Steuerelement SHALL das Benutzer-Popup öffnen; das Popup SHALL den Anzeigenamen, die E-Mail, „Mein Profil“ und „Abmelden“ enthalten. Ein optionaler Link zur externen Konto-Verwaltung SHALL nur bei vertrauenswürdig konfigurierter Provider-URL erscheinen.

#### Scenario: Vor- und Nachname vorhanden
- **WHEN** ein angemeldeter Benutzer die effektiven Namensbestandteile „Max“ und „Beispiel“ hat
- **THEN** zeigt der Avatar die Buchstaben „MB“ in einem Kreis
- **AND** das Popup zeigt den vollständigen Anzeigenamen und die E-Mail

#### Scenario: Namen fehlen oder enthalten Unicode
- **WHEN** nur ein Namensbestandteil oder kein gültiger Vor-/Nachname verfügbar ist
- **THEN** zeigt der Avatar höchstens die vorhandenen Initialen oder ein neutrales Benutzer-Symbol
- **AND** niemals ein Bild aus einem OIDC-`picture`-Claim oder einer externen Quelle
- **AND** Unicode-Zeichen werden ohne byteweise Zerstückelung verarbeitet

#### Scenario: Profil wird lokal geändert
- **WHEN** der Benutzer erfolgreich einen lokalen Vor- oder Nachnamen speichert
- **THEN** Avatar und Menü übernehmen die effektiven Werte ohne Neuanmeldung

#### Scenario: Popup-Bedienung auf Desktop und Mobil
- **WHEN** ein Benutzer mit Maus, Touch oder Tastatur den Avatar aktiviert
- **THEN** ist das Popup erreichbar, mit beschriftetem Auslöser und sichtbarem Fokus
- **AND** Escape oder ein Klick außerhalb schließen das Popup
- **AND** „Mein Profil“ führt zur geschützten Profilansicht und „Abmelden“ ruft die bestehende Abmeldung auf

#### Scenario: Abmeldung oder Identitätswechsel bei laufendem Profilabruf
- **WHEN** eine Profilantwort erst nach Logout oder Wechsel des OIDC-Subjects eintrifft
- **THEN** wird die Antwort der alten Identität nicht im Menü oder Avatar angezeigt
- **AND** das Popup wird geschlossen

#### Scenario: Externe Konto-Verwaltung nicht konfiguriert
- **WHEN** keine vertrauenswürdige Account-Management-URL konfiguriert ist
- **THEN** erscheint kein erfundener oder hardcodierter Keycloak-Link im Popup

#### Scenario: Anonymes Browserfenster
- **WHEN** der Besucher nicht angemeldet ist
- **THEN** erscheint weiterhin die Login-Aktion statt des Profil-Avatars
