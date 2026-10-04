## 1. Tenant-Grenze

- [x] 1.1 Unvalidierte Bearer-Payloads nicht mehr in TenantMiddleware dekodieren.
- [x] 1.2 TenantValidationMiddleware nur mit bereits verifiziertem Principal ausfuehren.
- [x] 1.3 Authorization-Header allein nicht als authentifiziert fuer Rate-Limit-Multiplikator behandeln.

## 2. Rate-Limit-Fallback

- [x] 2.1 Speicherbegrenzten lokalen Sliding-Window-Limiter implementieren.
- [x] 2.2 OIDC Token Exchange bei Valkey-Fail-Open lokal begrenzen.
- [x] 2.3 Oeffentliche Selbstregistrierung bei Valkey-Fail-Open lokal strenger begrenzen.
- [x] 2.4 Normale Business-Endpunkte weiterhin fail-open behandeln.

## 3. Tests

- [x] 3.1 Gefaelschtes Bearer-`sub` wird nicht in Tenant-Kontext uebernommen.
- [x] 3.2 Bearer-Header allein erhaelt keinen Auth-Multiplikator.
- [x] 3.3 Token-Exchange wird nach lokalem Limit mit 429 blockiert.
- [x] 3.4 Selbstregistrierung wird nach lokalem Limit mit 429 blockiert.
- [x] 3.5 Normaler Business-Endpunkt bleibt bei Redis-Ausfall verfuegbar.

## 4. Verifikation

- [ ] 4.1 Backend Unit-/Integrationstests erfolgreich.
- [ ] 4.2 Backend Coverage >80 Prozent.
- [ ] 4.3 CodeQL und Security Scans erfolgreich.