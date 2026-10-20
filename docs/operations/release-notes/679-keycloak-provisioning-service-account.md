### Keycloak-Provisionierung über Service Account statt master-Admin

**Betroffen:**

Produktivinstallationen mit `IDP_PROVISIONING_ENABLED=true` und `IDP_PROVISIONING_PROVIDER=keycloak`. Das Backend meldet sich nicht mehr mit einem Benutzer des Realms `master` an, sondern per `client_credentials` mit einem eigenen Client im App-Realm. Der Produktionsstart (API, Worker, Beat) wird abgelehnt, wenn `IDP_PROVISIONING_KEYCLOAK_CLIENT_ID` oder `IDP_PROVISIONING_KEYCLOAK_CLIENT_SECRET` fehlen oder `IDP_PROVISIONING_KEYCLOAK_ADMIN_USERNAME`/`_PASSWORD` noch gesetzt sind. Installationen mit Webhook-Provider oder ohne Provisionierung sind nicht betroffen.

**Vor dem Update:**

- Im Realm `nak-planner` einen Client `nak-planner-provisioning` anlegen: *Client authentication* an, *Service accounts roles* an, *Standard flow* und *Direct access grants* aus.
- Dem Service Account nur die Rollen `manage-users` und `view-users` des Clients `realm-management` zuweisen.
- In `.env` `IDP_PROVISIONING_KEYCLOAK_CLIENT_ID=nak-planner-provisioning` und `IDP_PROVISIONING_KEYCLOAK_CLIENT_SECRET=<Secret aus dem Credentials-Tab>` setzen und `IDP_PROVISIONING_KEYCLOAK_ADMIN_USERNAME`/`_PASSWORD` entfernen.
- Optional `IDP_PROVISIONING_KEYCLOAK_INVITE_REDIRECT_URI=https://<APP_HOST>/` setzen und diese URI im Frontend-Client unter *Valid redirect URIs* ergänzen. `IDP_PROVISIONING_KEYCLOAK_INVITE_LIFESPAN_SECONDS` (Default 259200, erlaubt 3600 bis 604800) bestimmt die Gültigkeit des Einladungslinks.
- Im Realm SMTP unter *Realm settings → Email* mit *Test connection* prüfen.

**Nach dem Update:**

- Prüfen, dass API, Worker und Beat starten.
- Eine Testregistrierung freigeben: `idp_provision_status` muss `CREATED_INVITED` (bzw. `EXISTING…`) sein, und die Einladungsmail muss ankommen.
- Danach den bisherigen Provisioning-Benutzer im Realm `master` löschen.
