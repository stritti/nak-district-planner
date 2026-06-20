## Why

Aktuell haben **öffentliche Endpunkte kein Rate Limiting** (SEC-016). Dies ermöglicht:

1. **Denial of Service Angriffe**: Angreifer können durch massive Requests die API überlasten
2. **Ressourcen-Erschöpfung**: Hohe Serverlast durch automatisierte Scraping-Tools
3. **Kostenexplosion**: Bei Cloud-Hosting können hohe Request-Zahlen zu hohen Kosten führen
4. **Compliance-Verstoss**: OWASP A05 (Security Misconfiguration) und CIS Control 4.1 sind nicht erfüllt

Besonders betroffen:
- `/api/v1/export/{token}/calendar.ics` - ICS-Export (kann von jedem mit Token aufgerufen werden)
- `/api/v1/auth/oidc/discovery` - OIDC Discovery (unauthentifiziert)
- `/api/v1/auth/oidc/token` - Token Exchange (unauthentifiziert)

## What Changes

### Neue Fähigkeiten
- `rate-limiting`: Systemweites Rate Limiting für API-Endpunkte
- `rate-limit-configuration`: Konfigurierbare Limits pro Endpunkt
- `rate-limit-monitoring`: Monitoring und Alerting bei Rate-Limit-Verstößen

### Geänderte Fähigkeiten
- Alle öffentlichen Endpunkte haben Rate Limiting
- Fehlerantworten enthalten Rate-Limit-Informationen
- Requests über dem Limit erhalten HTTP 429 (Too Many Requests)

## Capabilities

### New Capabilities
- **rate_limiter**: Redis-basierter Rate Limiter mit Sliding Window
- **rate_limit_middleware**: FastAPI Middleware zur Anwendung von Rate Limits
- **rate_limit_config**: Konfiguration von Limits pro Endpunkt/Endpunktgruppe
- **rate_limit_headers**: Standardisierte Rate-Limit Header in Responses
- **rate_limit_monitoring**: Metriken und Alerting für Rate Limiting

### Modified Capabilities
- **export_endpoint**: Rate Limiting für ICS-Export (60 Requests/Minute pro Token)
- **auth_endpoints**: Rate Limiting für OIDC Endpunkte (100 Requests/Minute pro IP)
- **api_endpoints**: Rate Limiting für alle API Endpunkte (200 Requests/Minute pro User)

## Impact

### Backend
- Neue Abhängigkeit: `redis` (bereits vorhanden)
- Neue Middleware für Rate Limiting
- Neue Konfiguration für Rate Limits
- Neue Header in API Responses

### Frontend
- Handling von HTTP 429 Fehlern
- Anzeige von Rate-Limit-Informationen

### Infrastruktur
- Redis wird für Rate Limiting genutzt (bereits vorhanden)
- Ggf. zusätzliche Redis-Instanzen für hohe Last

### Betrieb
- Monitoring von Rate-Limit-Verstößen
- Alerting bei ungewöhnlichen Mustern
- Regelmäßige Review der Rate-Limit-Konfiguration

## Success Criteria

- [ ] Alle öffentlichen Endpunkte haben Rate Limiting
- [ ] Rate Limits sind konfigurierbar pro Endpunkt
- [ ] HTTP 429 wird bei Überschreitung zurückgegeben
- [ ] Rate-Limit Header sind in Responses enthalten:
  - `X-RateLimit-Limit`: Maximale Requests
  - `X-RateLimit-Remaining`: Verbleibende Requests
  - `X-RateLimit-Reset`: Zeit bis Reset (Sekunden)
  - `Retry-After`: Zeit bis nächste Request erlaubt (bei 429)
- [ ] Performance-Impact < 1ms pro Request
- [ ] Rate Limiting ist in Staging getestet
- [ ] Dokumentation für Rate-Limit-Konfiguration

## Open Questions

1. Sollten verschiedene Limits für authentifizierte vs. unauthentifizierte Nutzer gelten?
   - **Empfehlung:** Ja, authentifizierte Nutzer höhere Limits

2. Sollten Limits pro IP oder pro User gelten?
   - **Empfehlung:** Pro User (authentifiziert) oder pro IP (unauthentifiziert)

3. Sollten Burst-Limits implementiert werden?
   - **Empfehlung:** Ja, für kurze Spitzen

4. Sollten Rate-Limit-Verstöße geloggt werden?
   - **Empfehlung:** Ja, für Security Monitoring

5. Sollten Rate Limits dynamisch anpassbar sein?
   - **Empfehlung:** Nein, statische Konfiguration reicht

