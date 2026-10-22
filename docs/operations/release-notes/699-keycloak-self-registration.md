### Self-Registration statt Backend-Provisionierung

**Betroffen:**

Produktivinstallationen mit `IDP_PROVISIONING_ENABLED=true` und `IDP_PROVISIONING_PROVIDER=keycloak`. Der Provisioner wurde entfernt: Das Backend hält kein Keycloak-Admin-Credential (weder Client-Secret noch Admin-Passwort) mehr. Accounts legt nun jede Person selbst über die Self-Registration des Realms an (mit E-Mail-Verifikation; die E-Mail-Adresse ist der Benutzername). Der Start verweigert in jeder Umgebung, wenn `IDP_PROVISIONING_PROVIDER=keycloak` noch gesetzt ist.

**Vor dem Update:**

- `idp-deploy/keycloak/setup_keycloak_realm.py` erneut ausführen: es aktiviert die Self-Registration (`registrationAllowed`, `verifyEmail`, `registrationEmailAsUsername`) und löscht den bisherigen Provisioning-Client `nak-planner-provisioning`, damit dessen Secret ungültig wird.
- In `.env` `IDP_PROVISIONING_PROVIDER=keycloak` und alle `IDP_PROVISIONING_KEYCLOAK_*`-Variablen entfernen (oder `IDP_PROVISIONING_ENABLED=false` setzen). Der Start bricht sonst mit einem Fehler ab.
- Die Registrierungsendpunkte des Realums mit einem Rate-Limit am Reverse-Proxy schützen; siehe `docs/operations/production-compose.md`.

**Nach dem Update:**

- Prüfen, dass API, Worker und Beat starten.
- Eine Testregistrierung: Das Konto wird selbst angelegt, die E-Mail verifiziert; die Freigabe der Registrierung verknüpft das Konto beim ersten Login über die verifizierte E-Mail-Adresse.
- Der bisherige Provisioning-Client existiert nicht mehr; ein verbliebenens Secret in alten `.env`-Kopien ist ungültig.
