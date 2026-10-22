## Context

Heute: Registrierung in der App (anonym oder mit Token) → `PENDING` → Freigabe durch Bezirksadmin mit Rolle und Scope → optional legt das Backend den Benutzer per Admin-API in Keycloak an und schickt `VERIFY_EMAIL`/`UPDATE_PASSWORD`. Unabhängig davon verknüpft `get_current_user_with_memberships` beim Login eine freigegebene, noch unverknüpfte Registrierung über die SQL-Funktion `link_approved_registration`, aber nur bei `email_verified=true` im Token (#461). Der Realm hat `registrationAllowed=false`.

Die Analyse in PR #681 ergab, dass jeder Admin-Zugang mit Scope `manage` Kontoübernahmen erlaubt. Entscheidung (2026-10-22): Das Backend hält kein Keycloak-Admin-Secret mehr.

## Goals / Non-Goals

**Goals:**
- Kein Keycloak-Admin-Secret und kein Keycloak-Admin-Code im Backend.
- Neue Benutzer kommen ohne Admin-Eingriff in Keycloak zu einem Konto, und die Freigabe greift beim ersten Login.
- Bestehende Installationen werden beim Start auf die alte Konfiguration hingewiesen, statt still weiterzulaufen.

**Non-Goals:**
- Keine Änderung am Webhook-Provider; wer extern provisioniert, verantwortet dessen Rechte selbst.
- Keine Änderung am Auto-Link (#461) und keine neue Datenbankmigration.
- Keine eigene CAPTCHA-Implementierung in der App.

## Decisions

**Selbstregistrierung in Keycloak statt Admin-Anlage.** Alternativen: FGAP v2 mit akzeptiertem Übernahmerisiko (verworfen, siehe Why) und manuelle Anlage durch Bezirksadmins in der Admin-Konsole (verworfen, weil Bezirksadmins dann Keycloak-Adminrechte bräuchten, die dieselben Übernahmepfade öffnen). Ein selbst angelegtes Konto ohne Membership erhält nur `403` mit „Freigabe ausstehend“; damit ist offene Registrierung unkritisch.

**E-Mail-Verifizierung bleibt Pflicht.** Ohne `verifyEmail` könnte jemand ein Konto mit fremder Adresse anlegen; der Auto-Link verweigert dann zwar die Verknüpfung (`email_verified` fehlt), aber die Pflicht schließt den Weg schon in Keycloak. Das Skript setzt `registrationAllowed=true` nur zusammen mit `verifyEmail=true` und `registrationEmailAsUsername=true`, damit es keine zweite Kennung neben der E-Mail gibt.

**Start verweigern statt Einstellung ignorieren.** Bei `IDP_PROVISIONING_PROVIDER=keycloak` würde ein stilles Ignorieren Freigaben ohne Einladung hinterlassen. Ein klarer Startfehler, der auf die Upgrade-Notiz verweist, ist sicherer. Die übrigen `IDP_PROVISIONING_KEYCLOAK_*`-Variablen werden nur gemeldet, wenn der Provider `keycloak` ist; sonst sind sie wirkungslos.

**Provisioning-Client löschen.** Das Skript löscht `nak-planner-provisioning`, falls vorhanden, statt nur die Rollen zu entziehen. So wird das Secret sofort ungültig, und es bleibt nichts, das versehentlich wieder Rechte bekommt. Der Name ist per `--provisioning-client-id` überschreibbar, wie bisher.

**Registrierungsseite führt zur Kontoanlage.** Nach dem Absenden zeigt die Seite einen Button „Konto anlegen“, der den Login mit `prompt=create` startet (Keycloak zeigt dann das Registrierungsformular). Die App baut die Autorisierungs-URL selbst (PKCE in `oidcAuthorization.getAuthorizationUrl`, kein `oidc-client-ts`); die Funktion bekommt dafür einen optionalen Parameter `prompt`, und `useOIDC` reicht ihn durch. Ist der Benutzer bereits angemeldet, sendet die Seite den Access Token mit, und die Registrierung bekommt sofort `user_sub`. Reihenfolge ist frei: Konto zuerst oder Registrierung zuerst führen beide über den Auto-Link zum Ziel.

## Risks / Trade-offs

- [Spam-Konten in Keycloak] → Konten ohne Membership gewähren nichts. Doku empfiehlt Rate-Limit auf `/realms/*/login-actions/registration` am Reverse Proxy und optional den reCAPTCHA-Schritt im Registrierungsflow; ungenutzte, unverifizierte Konten lassen sich in Keycloak per Admin-Konsole bereinigen.
- [Bewerber legt Konto mit anderer E-Mail an als in der Registrierung] → Auto-Link greift nicht; der Bewerber sieht „Freigabe ausstehend“. Registrierungsseite und Freigabe-Mail nennen die Bedingung; der Bezirksadmin kann die Registrierung mit korrigierter E-Mail neu anlegen lassen.
- [Bestehende Installationen mit ausstehenden Einladungen] → Bereits verschickte Einladungslinks bleiben bis zum Ablauf (max. 7 Tage) gültig; neue Freigaben verschicken keine Einladung mehr. Upgrade-Notiz beschreibt das.
- [Konto-Enumeration über das Registrierungsformular] → Keycloak meldet bei einer bereits vergebenen E-Mail-Adresse, dass das Konto existiert. Das Rate-Limit am Reverse Proxy (siehe oben) begrenzt das Abtasten; ein vollständiger Schutz ist mit der Selbstregistrierung nicht erreichbar und wird in der Doku als bewusste Folge genannt.
- [Betreiber, die der Upgrade-Notiz zu 1.5.0 gefolgt sind] → Die Notiz `679-keycloak-provisioning-service-account.md` richtet genau den Service Account ein, den dieser Change entfernt. Die neue Upgrade-Notiz nennt das ausdrücklich als Ablösung und führt durch das Entfernen von Konfiguration und Client.
- [Webhook-Provider mit eigenem Keycloak-Zugang] → Außerhalb dieses Changes; die Doku weist darauf hin, dass dort dieselben Übernahmepfade gelten.

## Migration Plan

1. `IDP_PROVISIONING_PROVIDER=keycloak` und alle `IDP_PROVISIONING_KEYCLOAK_*` aus `.env` entfernen (oder `IDP_PROVISIONING_ENABLED=false`).
2. Setup-Skript erneut ausführen: aktiviert Selbstregistrierung mit E-Mail-Verifizierung und löscht den Provisioning-Client.
3. App neu starten; eine Testregistrierung mit neuem Keycloak-Konto durchspielen.
4. Rollback: vorherige App-Version und Konfiguration; der Provisioning-Client muss dann neu angelegt werden (Setup-Skript der Vorversion).
