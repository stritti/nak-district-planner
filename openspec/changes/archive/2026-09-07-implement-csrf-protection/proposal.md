## Why

Aktuell gibt es **keinen CSRF-Schutz** (SEC-004) für state-changing Requests. Dies ermöglicht:

1. **Cross-Site Request Forgery Angriffe**: Angreifer können authentifizierte Nutzer dazu bringen, unerwünschte Aktionen auszuführen
2. **Session Hijacking**: Durch CSRF können Sessions kompromittiert werden
3. **Compliance-Verstoss**: OWASP A01 (Broken Access Control) ist nicht vollständig erfüllt
4. **Sicherheitsrisiko**: Besonders kritisch für Admin-Operationen

## What Changes

### Neue Fähigkeiten
- `csrf-protection`: CSRF-Schutz für alle state-changing Requests
- `csrf-token-management`: Generierung und Validierung von CSRF-Tokens
- `csrf-middleware`: FastAPI Middleware für CSRF-Prüfung

### Geänderte Fähigkeiten
- Alle state-changing Requests (POST, PUT, PATCH, DELETE) erfordern CSRF-Token
- Frontend muss CSRF-Token in Requests einbinden
- API gibt CSRF-Token in Responses zurück

## Capabilities

### New Capabilities
- **csrf_token_service**: Service zur Generierung und Validierung von CSRF-Tokens
- **csrf_middleware**: FastAPI Middleware zur automatischen CSRF-Prüfung
- **csrf_cookie**: CSRF-Token in Cookie (script-readable für Double-Submit Pattern)
- **csrf_header**: CSRF-Token im Request Header
- **csrf_exemption**: Ausnahmen für bestimmte Endpunkte (z.B. API-Key Auth)

### Modified Capabilities
- **web_form_submission**: Erfordert CSRF-Token
- **api_state_changes**: Erfordert CSRF-Token (außer API-Key Auth)
- **auth_flow**: CSRF-Token Management im OIDC Flow

## Impact

### Backend
- Neue Middleware für CSRF-Prüfung
- Neuer Service für Token-Management
- Neue Konfiguration für CSRF-Einstellungen

### Frontend
- CSRF-Token muss in Requests eingebunden werden
- Token muss aus Cookie oder Response extrahiert werden

### Infrastruktur
- Keine Änderungen

### Betrieb
- Keine Änderungen

## Success Criteria

- [ ] Alle state-changing Requests erfordern CSRF-Token
- [ ] CSRF-Tokens sind kryptografisch sicher (HMAC-SHA256)
- [ ] CSRF-Tokens haben begrenzte Lebensdauer (z.B. 24 Stunden)
- [ ] CSRF-Tokens sind in Cookies gespeichert (script-readable für Double-Submit Pattern; **HttpOnly bewusst weggelassen**, damit JavaScript das Token lesen und im `X-CSRF-Token` Header mitsenden kann)
- [ ] CSRF-Tokens werden im Header gesendet (`X-CSRF-Token`)
- [ ] API-Key Auth ist von CSRF-Schutz ausgenommen
- [ ] OIDC Flow funktioniert mit CSRF-Schutz
- [ ] Performance-Impact < 0.5ms pro Request
- [ ] CSRF-Schutz ist in Staging getestet
- [ ] **Browser-seitige Integration verifiziert** (Frontend sendet Token korrekt im Header bei state-changing Requests)

## Open Questions

1. Sollten CSRF-Tokens pro Session oder pro Request generiert werden?
   - **Empfehlung:** Pro Session (Double-Submit Pattern)

2. Sollten CSRF-Tokens verschlüsselt oder nur signiert werden?
   - **Empfehlung:** Signiert (HMAC), nicht verschlüsselt

3. Sollten CSRF-Tokens in Cookies oder Local Storage gespeichert werden?
   - **Empfehlung:** Cookies (script-readable für Double-Submit Pattern; **HttpOnly weggelassen**, damit JavaScript das Token lesen kann)

4. Sollten CSRF-Tokens für API-Endpunkte gelten?
   - **Empfehlung:** Ja, außer für API-Key Auth

5. Wie mit CORS umgehen?
   - **Empfehlung:** CORS muss korrekt konfiguriert sein

6. **Ist die Frontend-Integration (`useCSRF()` Composable) in E2E-Tests gegen echte Browser-Requests verifiziert?**
   - **Status:** Offen — muss vor Abschluss des Changes verifiziert werden

