## Why

Approvte, noch unverknuepfte Registrierungen (inkl. `DISTRICT_ADMIN`) wurden beim Login automatisch an den ersten Aufrufer mit passender E-Mail gebunden (Issue #461). Die E-Mail stammte ungeprueft aus dem Token-Claim `email`; `email_verified` wurde nie geprueft, und ohne `email` wurde sogar `preferred_username` (falls mit `@`) verwendet. Analog hat der Keycloak-Provisioner eine Registrierung an ein bestehendes Keycloak-Konto gebunden, auch wenn dessen E-Mail nicht verifiziert war. Wer eine fremde Adresse unverifiziert beim IdP registrieren kann, konnte so die freigegebene Rolle uebernehmen.

## What Changes

- Auto-Verknuepfung (`link_approved_registration`) nur, wenn das Token einen `email`-Claim **und** `email_verified` exakt als Boolean `true` liefert. String-Werte (`"true"`) werden bewusst abgelehnt (fail closed).
- Der `preferred_username`-Fallback bleibt nur fuer die Anzeige (`User.email`) erhalten, wird aber nie als verifizierte E-Mail behandelt.
- Keycloak-Provisioner bindet nur an bestehende Konten mit `emailVerified=true`. Sonst bleibt die Registrierung unverknuepft (`idp_provision_status = EXISTING_UNVERIFIED[_INVITED]`); die Einladungsmail (falls aktiviert) geht an die Adresse selbst, die Verknuepfung erfolgt beim ersten Login mit verifizierter E-Mail. Der 409-Race beim Anlegen durchlaeuft dieselbe Pruefung.
- Die SQL-Funktion bleibt unveraendert: Sie prueft nur, dass `p_user_sub` dem Session-Subjekt entspricht. Das Gate fuer die E-Mail-Verifikation liegt in der Anwendungsschicht (dokumentiert); keine Migration.

## Capabilities

### New Capabilities
- `user-onboarding`: Verifizierte E-Mail als Voraussetzung fuer automatische Registrierungs-Verknuepfung und IdP-Bindung.

### Modified Capabilities
- (none)

## Impact

- Backend: `app/adapters/auth/oidc.py`, `app/adapters/api/deps.py`, `app/domain/models/user.py` (transientes Feld `email_verified`), `app/adapters/idp/keycloak_provisioner.py`.
- Betrieb: Der IdP muss `email_verified` im Access-Token bzw. Userinfo liefern (Keycloak: Scope `email`; Authentik: Scope-Mapping `email`, Verifikation per Flow/Property-Mapping). Fehlt der Claim, erfolgt keine Auto-Verknuepfung; die Freigabe muss dann manuell (Registrierung mit Login) erfolgen.
- Docs: `docs/approval-workflow.md`.
