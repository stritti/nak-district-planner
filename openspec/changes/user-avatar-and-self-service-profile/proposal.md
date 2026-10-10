## Why

In der Hauptnavigation zeigt der NAK-Bezirksplaner angemeldeten Personen aktuell einen langen Block aus Name und E-Mail (mobil ein generisches Benutzer-Icon). Das Dropdown ermöglicht nur die Abmeldung. Eigene, rein darstellungsbezogene Namensangaben können nicht selbst gepflegt werden. Die vorhandenen `users`-Namensfelder werden beim OIDC-Login aus Provider-Claims aktualisiert; direkte Bearbeitung dort wäre nicht dauerhaft zuverlässig.

## What Changes

- Der rechte Bereich der Navigation zeigt einen kreisrunden, generischen Avatar mit den Initialen aus Vor- und Nachname, ohne Profilbilder, Bild-URLs oder Uploads.
- Der Avatar öffnet das bestehende Dropdown, dessen Kopf weiterhin Name und E-Mail anzeigt. Aktionen: **Mein Profil** und **Abmelden**. Wenn eine geprüfte Provider-Kontoverwaltungs-URL konfiguriert ist, erscheint zusätzlich **Anmeldekonto verwalten**.
- Die geschützte Ansicht `/account` ermöglicht allen authentifizierten Personen, einschließlich `PENDING_APPROVAL`, den **lokalen Anzeigenamen** als Vor- und Nachname zu bearbeiten und auf IdP-Werte zurückzusetzen.
- E-Mail, Anmeldekennung, Passwort, OIDC-Subject, E-Mail-Verifikation, Rollen und Mitgliedschaften sind **nicht** über das lokale Profil änderbar. Änderungen am Identitätskonto erfolgen beim jeweiligen OIDC-Provider.
- Profiländerungen gelten nur innerhalb des Bezirksplaners. Eine Keycloak-Synchronisation und Keycloak-spezifische Admin-API sind **nicht** erforderlich. Die bestehende IdP-agnostische Authentifizierung bleibt unverändert.
- Eine separate, auf das eigene `sub` begrenzte Persistenz bewahrt lokale Namensüberschreibungen davor, bei der Aktualisierung der `users`-Tabelle durch OIDC-Claims verloren zu gehen.

## Capabilities

### New Capabilities
- `user-profile`: Selbstbedienung, Datenhoheit, sichere lokale Namensüberschreibungen, REST-Vertrag und Rücksetzung.

### Modified Capabilities
- `frontend-ux`: Generischer Initialen-Avatar, zugängliches Dropdown und Navigation zur Profilbearbeitung.

## Impact

- Frontend: `AppNav.vue`, getrennte Avatar-/Menükomponente, `/account`-Ansicht, Router und ein profilbezogener API-/Store-Pfad.
- Backend: authentifizierte Self-Service-Endpunkte `GET/PUT /api/v1/profile/me`, eigene Persistenz mit Alembic-Migration und benutzerbezogenen RLS-Regeln. Die Tabelle `users` bleibt vom OIDC-Lifecycle verwaltet.
- Sicherheit: Keine Änderung von OIDC, Registrierung, Identität, Passwortverwaltung, RBAC oder Freigabeprozessen; keine beliebige `user_sub`-Angabe durch Clients.
- Tests: Unit-, Komponenten-, API-/RLS-Integrations- und E2E-Tests; >80 % Coverage je betroffener Production-Datei und negative Szenarien.

## Non-Goals

- Eigene Avatarbilder, externe Bilddienste, automatische Initialen-Farben anhand personenbezogener Merkmale.
- Änderungen von IdP-E-Mail/Passwort oder direkte Keycloak-/Authentik-Profile-API-Aufrufe aus dem Planner.
- Adminseitige Bearbeitung fremder Profile, zusätzliche Rollen, Account-Löschung oder Umstellung der bestehenden OIDC-Authentifizierung.
