### Keycloak: Selbstregistrierung statt Provisionierung durch das Backend

**Betroffen:**

Installationen, die das Backend Keycloak-Benutzer anlegen und einladen lassen (`IDP_PROVISIONING_ENABLED=true` mit `IDP_PROVISIONING_PROVIDER=keycloak`), also alle, die der Upgrade-Notiz „Keycloak-Provisionierung über Service Account statt master-Admin“ aus Version 1.5.0 gefolgt sind. Der Keycloak-Provisioner ist entfernt, das Backend hält kein Keycloak-Admin-Credential mehr. Grund: Jedes Admin-Recht mit dem Scope `manage` erlaubt in Keycloak Kontoübernahmen (E-Mail ändern und Einladung auslösen, OTP-/WebAuthn-Credentials löschen, externe Identität verknüpfen), auch mit feingranularen Berechtigungen. Jetzt legt jede Person ihr Konto selbst an (Selbstregistrierung mit verifizierter E-Mail, die Adresse ist der Benutzername); die Freigabe der Registrierung verknüpft das Konto beim ersten Login über die verifizierte E-Mail. Ist `IDP_PROVISIONING_PROVIDER=keycloak` mit aktivierter Provisionierung noch gesetzt, verweigert das Backend in jeder Umgebung den Start. Der Webhook-Provider ist unverändert; ein externer Provisioner mit eigenem Keycloak-Zugang unterliegt weiterhin denselben Übernahmerisiken.

**Vor dem Update:**

- Ein aktuelles Backup nach dem Produktions-Runbook erstellen.
- In `.env` `IDP_PROVISIONING_PROVIDER=keycloak` und alle `IDP_PROVISIONING_KEYCLOAK_*`-Variablen entfernen (oder `IDP_PROVISIONING_ENABLED=false` setzen). Auch Kopien der Datei mit dem alten Client-Secret bereinigen.
- `idp-deploy/keycloak/setup_keycloak_realm.py` gegen das Realm ausführen (Aufruf siehe `docs/operations/production-compose.md`). Das Skript aktiviert `registrationAllowed`, `verifyEmail` und `registrationEmailAsUsername` und **löscht** den früheren Client `nak-planner-provisioning`, sodass sein Secret ungültig wird. Wer das Realm von Hand pflegt, schaltet *User registration*, *Email as username* und *Verify email* ein und löscht den Client in der Admin-Konsole.
- Im Realm unter *Realm settings → Email* ein SMTP-Relay eintragen und mit *Test connection* prüfen: Keycloak versendet die Bestätigungsmail der Registrierung.
- Das Rate-Limit für die öffentlichen Registrierungsrouten sicherstellen: Die mitgelieferte Traefik-Konfiguration (`deploy/traefik/dynamic/keycloak.yml`, bei vorhandenem Traefik `deploy/compose/existing-traefik.yml`) begrenzt sie jetzt auf 10 Anfragen je Minute und Client. Wer einen eigenen Reverse Proxy nutzt, richtet für `/realms/<Realm>/login-actions/registration` und `/realms/<Realm>/protocol/openid-connect/registrations` eine gleichwertige Begrenzung ein.

**Nach dem Update:**

- Prüfen, dass API, Worker und Beat starten und `alembic current` unverändert ist (keine Migration).
- Eine Testregistrierung durchspielen: auf der Registrierungsseite einreichen, „Konto anlegen“ wählen, das Konto mit **derselben** E-Mail-Adresse anlegen und bestätigen, als Bezirksadmin freigeben, dann anmelden. Vor der Freigabe antworten geschützte Endpunkte mit `403` („Freigabe ausstehend“), danach hat die Person ihre Rolle.
- Bewerber informieren, deren Registrierung noch aussteht oder die bereits eine Einladung erhalten haben: Neue Freigaben verschicken keine Einladung mehr; bereits verschickte Einladungslinks bleiben bis zum Ablauf gültig (höchstens sieben Tage). Wer noch kein Konto hat, legt es über die Registrierungsseite oder den Login an.
- Rollback: vorherige App-Version und Konfiguration verwenden. Der gelöschte Provisioning-Client muss dann neu angelegt werden (Setup-Skript der Vorversion).
