## Context

`KeycloakProvisioningAdapter` holt sich bei jeder Freigabe ein Token über `/realms/master/protocol/openid-connect/token` mit `grant_type=password` und `client_id=admin-cli`. Danach sucht es den Benutzer per E-Mail, legt ihn bei Bedarf an und ruft `PUT /admin/realms/{realm}/users/{id}/execute-actions-email` ohne Query-Parameter auf. Die Settings liegen in `app/config.py`, der Produktions-Guard prüft dort bereits URL, Realm und Admin-Zugangsdaten. Das Realm-Skript `idp-deploy/keycloak/setup_keycloak_realm.py` legt Realm, Public Client und Testbenutzer an, setzt aber keine Sicherheits-Defaults. Motivation siehe `proposal.md`, Anforderungen siehe `specs/approved-user-onboarding/spec.md`.

## Goals / Non-Goals

**Goals:**
- Kleinstmögliche Berechtigung für das Backend gegenüber Keycloak.
- Einladungslinks mit definierter Laufzeit und Rücksprung in die App.
- Reproduzierbare, sichere Realm-Grundeinstellungen über das vorhandene Setup-Skript.

**Non-Goals:**
- Kein eigener Mailserver und kein Mailversand der App für Einladungen; Keycloak verschickt die Einladung über sein SMTP-Relay.
- Kein Token-Caching: Freigaben sind selten, ein Token pro Freigabe genügt.
- Keine Erzwingung von OTP/Passkey durch die App; das bleibt eine Realm-Einstellung, die dokumentiert wird.
- Keine Änderung am Webhook-Provider oder am Verknüpfungs-Gate über `email_verified`.

## Decisions

**Client Credentials statt Password-Grant.** Ein Confidential Client `nak-planner-provisioning` im App-Realm mit aktiviertem Service Account und nur `realm-management: manage-users, view-users`. Token-Endpunkt ist `/realms/{realm}/protocol/openid-connect/token`. `manage-users` deckt Anlegen und `execute-actions-email` ab, `view-users` die Suche. Alternative: weiter ein Admin-Benutzer, aber im App-Realm statt master. Verworfen, weil weiterhin ein interaktiv nutzbares Passwort existiert und Rollen schwerer zu begrenzen sind.

**Altes Verfahren ersatzlos entfernen.** Kein Fallback auf Password-Grant, damit kein zweiter, schwächerer Pfad bleibt. Der Produktions-Guard lehnt gesetzte `IDP_PROVISIONING_KEYCLOAK_ADMIN_*` aktiv ab, damit das Update nicht still mit kaputter Provisionierung startet. Außerhalb von Produktion werden die alten Variablen ignoriert.

**Laufzeit und Rücksprung als Settings.** `IDP_PROVISIONING_KEYCLOAK_INVITE_LIFESPAN_SECONDS` (Pydantic `Field(ge=3600, le=604800)`, Default 259200) wird immer als `lifespan` gesendet. `IDP_PROVISIONING_KEYCLOAK_INVITE_REDIRECT_URI` ist optional; nur wenn gesetzt, werden `client_id` (= `OIDC_CLIENT_ID`) und `redirect_uri` mitgeschickt. Keycloak prüft die URI gegen die Redirect-URIs des Clients, daher keine eigene Allowlist. Ziel ist die App-Wurzel (nicht `/auth/callback`, das ohne Code fehlschlägt); das Setup-Skript nimmt sie in die Redirect-URIs auf. In Produktion muss die URI `https://` verwenden.

**Realm-Defaults im Setup-Skript.** `registrationAllowed=false`, `verifyEmail=true`, `loginWithEmailAllowed=true`, `resetPasswordAllowed=true`, `bruteForceProtected=true`, `passwordPolicy="length(15) and notUsername and notEmail"`. Keine Zeichenklassen-Regeln (NIST SP 800-63B). Bestehende Realms werden per `PUT` auf diese Werte gebracht; das Skript gibt das Client-Secret nicht aus (kein Secret in Terminal-Logs); es wird im Credentials-Tab abgelesen.

## Risks / Trade-offs

- [Bestehende Keycloak-Installationen starten nach dem Update nicht mehr] → Klare Fehlermeldung des Guards, Migrationsschritte im Runbook und in den Release Notes.
- [`manage-users` erlaubt auch Rollen- und Gruppenzuordnungen im App-Realm] → Die Anwendung autorisiert über eigene Memberships, nicht über Keycloak-Rollen; der Wirkungsbereich bleibt auf einen Realm begrenzt statt Vollzugriff über `master`. Feingranulare Admin-Berechtigungen (Keycloak FGAP v2) wären eine weitere Einschränkung und sind ein möglicher Folge-Change.
- [Setup-Skript gegen Produktion legt Testbenutzer an] → Testbenutzer nur noch mit `--create-test-user`.
- [Client-Secret liegt weiterhin in der `.env`] → Secret ist auf User-Verwaltung eines Realms begrenzt und rotierbar; Rotation im Runbook beschreiben.
- [Realm-SMTP fehlt, Einladung scheitert] → Fehler wird wie heute als `idp_provision_error` gespeichert; Runbook verlangt SMTP-Test über „Test connection“ im Realm.
- [Zu kurze Laufzeit, Einladung verfällt] → 72 h als Default; ein Realm-Admin sendet die Aktionen in der Keycloak-Konsole erneut (Benutzer → *Credentials* → *Credential reset*). Ein Resend-Endpunkt in der App ist nicht Teil dieses Changes.

## Migration Plan

1. Setup-Skript gegen den bestehenden Realm laufen lassen oder Client manuell anlegen (Confidential, Service Account an, Standard Flow aus, Rollen `manage-users`, `view-users`).
2. `IDP_PROVISIONING_KEYCLOAK_CLIENT_ID`/`_CLIENT_SECRET` setzen, `IDP_PROVISIONING_KEYCLOAK_ADMIN_*` entfernen, optional Redirect-URI und Laufzeit setzen.
3. Backend neu starten; eine Testfreigabe prüfen.
4. Rollback: vorheriges Image mit alten Variablen; der neue Client stört nicht und kann bleiben.
