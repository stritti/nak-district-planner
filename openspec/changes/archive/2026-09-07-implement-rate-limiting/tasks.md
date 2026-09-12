## Aufgaben für Rate-Limiting Implementierung

> **Hinweis (2026-09-07):** Dieses `tasks.md` existierte bisher nicht, obwohl das Feature über PR #172 ("feature/security-rate-limiting-sec-016") bereits implementiert und in `docs/security/rate-limiting.md` dokumentiert ist. Nachträglich gegen den Code-Stand erstellt.

### Kernfunktionalität
- [x] `RateLimiter` Klasse, Redis-basiert, Sliding Window (`app/application/rate_limiter.py`)
- [x] `RateLimitMiddleware` für FastAPI registriert
- [x] `RateLimitConfig` für Konfiguration
- [x] Burst Protection implementiert
- [x] Standard-Header in Responses: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`
- [x] HTTP 429 bei Überschreitung

### Nicht umgesetzt (Lücken gegenüber ursprünglichem Proposal)
- [ ] `RateLimitMetrics` / Monitoring & Alerting bei Rate-Limit-Verstößen *(nicht gefunden)*
- [ ] Frontend-Handling für HTTP 429 *(nicht gefunden — kein 429-spezifischer Code in `services/frontend/src`)*

### Bewertung
Das Kernrisiko (SEC-016: unbegrenzte öffentliche Endpunkte) ist behoben. Monitoring/Alerting und Frontend-UX für 429-Antworten fehlen noch als Politur, sind aber nicht sicherheitskritisch.
