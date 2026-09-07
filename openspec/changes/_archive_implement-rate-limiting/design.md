## Context

Der NAK District Planner bietet öffentliche API-Endpunkte, die aktuell ohne Rate Limiting zugänglich sind. Dies ermöglicht DoS-Angriffe und Ressourcen-Missbrauch.

Aktuell existierende Komponenten:
- FastAPI Backend mit strukturierten Routern
- Redis für Caching und Celery
- OIDC-basierte Authentifizierung
- Docker-basierte Infrastruktur

## Goals / Non-Goals

**Goals:**
- Alle öffentlichen Endpunkte vor DoS-Angriffen schützen
- Standardisierte Rate-Limit Header in Responses
- Konfigurierbare Limits pro Endpunkt
- Minimaler Performance-Impact (< 1ms pro Request)
- Compliance mit OWASP A05 und CIS 4.1

**Non-Goals:**
- DDoS-Schutz auf Netzwerkebene (ist Aufgabe des Hosting-Providers)
- IP-Blocking (kann später hinzugefügt werden)
- Geografisches Rate Limiting

## Decisions

### 1. Rate Limiting Algorithmus

**Sliding Window mit Redis:**
- Präziser als Fixed Window
- Verhindert Burst-Angriffe an Window-Grenzen
- Einfache Implementierung mit Redis Sorted Sets

```text
Beispiel: 60 Requests/Minute
- Jeder Request wird als Timestamp in Redis gespeichert
- Bei jedem Request: Zähle Requests in den letzten 60 Sekunden
- Wenn > 60: Verweigere mit HTTP 429
```text

### 2. Rate Limit Konfiguration

```yaml
# app/config.py
class RateLimitConfig:
    # Default Limits
    default_limit: int = 200
    default_window_seconds: int = 60
    
    # Endpunkt-spezifische Limits
    endpoint_limits: dict[str, dict] = {
        "/api/health": {"limit": 60, "window": 60},
        "/api/v1/auth/oidc/discovery": {"limit": 100, "window": 60},
        "/api/v1/auth/oidc/token": {"limit": 100, "window": 60},
        "/api/v1/export/*/calendar.ics": {"limit": 60, "window": 60},
        "/api/v1/events": {"limit": 100, "window": 60},
    }
    
    # Authentifizierte vs. unauthentifizierte Nutzer
    authenticated_multiplier: float = 2.0  # Authentifizierte Nutzer haben doppelte Limits
    
    # Burst Protection
    burst_limit: int = 10  # Maximale Requests in 1 Sekunde
    burst_window_seconds: int = 1
```python

### 3. Rate Limiter Implementierung

```python
# app/application/rate_limiter.py
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Optional
import hashlib

class RateLimiter:
    """Redis-basierter Rate Limiter mit Sliding Window."""
    
    def __init__(self, redis_url: str, default_limit: int = 200, default_window: int = 60):
        self.redis = redis.from_url(redis_url)
        self.default_limit = default_limit
        self.default_window = default_window
        
    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> tuple[bool, dict]:
        """
        Prüfe Rate Limit für einen Schlüssel.
        
        Args:
            key: Eindeutiger Identifier (z.B. "ip:192.168.1.1" oder "user:user123")
            limit: Maximale Requests (default: default_limit)
            window_seconds: Zeitfenster in Sekunden (default: default_window)
            
        Returns:
            tuple: (allowed: bool, info: dict)
            info: {
                "limit": int,
                "remaining": int,
                "reset": int,  # Sekunden bis Reset
                "retry_after": int | None,  # Sekunden bis nächste Request (bei Block)
            }
        """
        limit = limit or self.default_limit
        window = window_seconds or self.default_window
        
        redis_key = f"rate_limit:{key}:{window}"
        now = datetime.now()
        window_start = now - timedelta(seconds=window)
        
        # Zähle Requests im aktuellen Fenster
        pipe = self.redis.pipeline()
        
        # Entferne alte Einträge (vor window_start)
        pipe.zremrangebyscore(redis_key, 0, window_start.timestamp())
        
        # Füge aktuellen Request hinzu
        pipe.zadd(redis_key, {str(now.timestamp()): now.timestamp()})
        
        # Zähle aktuelle Requests
        pipe.zcard(redis_key)
        
        # Setze TTL für Key
        pipe.expire(redis_key, window)
        
        results = await pipe.execute()
        current_count = results[2]
        
        if current_count >= limit:
            # Rate Limit überschritten
            oldest_timestamp = await self.redis.zrange(redis_key, 0, 0, withscores=True)
            if oldest_timestamp:
                retry_after = int(oldest_timestamp[0][1] + window - now.timestamp())
            else:
                retry_after = window
            
            return False, {
                "limit": limit,
                "remaining": 0,
                "reset": window,
                "retry_after": max(1, retry_after),  # Mindestens 1 Sekunde
            }
        
        return True, {
            "limit": limit,
            "remaining": limit - current_count - 1,
            "reset": window,
            "retry_after": None,
        }
    
    async def get_rate_limit_status(self, key: str) -> dict:
        """Hole aktuellen Rate-Limit Status für Monitoring."""
        # Implementierung ähnlich check_rate_limit, aber ohne Request zu zählen
        pass
    
    def _generate_key(
        self,
        request: Request,
        endpoint: str,
        user_sub: Optional[str] = None,
    ) -> str:
        """Generiere eindeutigen Key für Rate Limiting."""
        # Für authentifizierte Nutzer: user_sub + endpoint
        if user_sub:
            return f"user:{user_sub}:{endpoint}"
        
        # Für unauthentifizierte Nutzer: IP + endpoint
        ip = request.client.host
        return f"ip:{ip}:{endpoint}"
```python

### 4. Rate Limit Middleware

```python
# app/adapters/api/middleware/rate_limit.py
from fastapi import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from typing import Callable, Awaitable
import time

class RateLimitMiddleware:
    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        config: RateLimitConfig,
    ):
        self.app = app
        self.rate_limiter = rate_limiter
        self.config = config
        self.skip_paths = {"/api/health"}  # Endpunkte ohne Rate Limiting
        
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Skip Rate Limiting für bestimmte Pfade
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        # Bestimme Endpunkt-Konfiguration
        endpoint_config = self._get_endpoint_config(request.url.path)
        limit = endpoint_config.get("limit", self.config.default_limit)
        window = endpoint_config.get("window", self.config.default_window)
        
        # Generiere Key
        user_sub = getattr(request.state, "user_sub", None)
        key = self.rate_limiter._generate_key(request, request.url.path, user_sub)
        
        # Prüfe Rate Limit
        allowed, info = await self.rate_limiter.check_rate_limit(key, limit, window)
        
        # Füge Rate-Limit Header hinzu
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        
        # Wenn Rate Limit überschritten
        if not allowed:
            response = JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": info["retry_after"],
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["retry_after"]),
                },
            )
        
        return response
        
    def _get_endpoint_config(self, path: str) -> dict:
        """Hole Konfiguration für Endpunkt."""
        # Suche nach passendem Pattern
        for pattern, config in self.config.endpoint_limits.items():
            if self._path_matches_pattern(path, pattern):
                return config
        return {}
        
    def _path_matches_pattern(self, path: str, pattern: str) -> bool:
        """Prüfe ob Pfad zu Pattern passt."""
        # Einfache Pattern-Matching (z.B. "/api/v1/export/*/calendar.ics")
        import fnmatch
        return fnmatch.fnmatch(path, pattern)
```python

### 5. Integration mit FastAPI

```python
# app/main.py
from app.application.rate_limiter import RateLimiter
from app.adapters.api.middleware.rate_limit import RateLimitMiddleware
from app.config import settings

# Initialisierung
redis_url = settings.redis_url
rate_limiter = RateLimiter(
    redis_url=redis_url,
    default_limit=200,
    default_window=60,
)

# Konfiguration
rate_limit_config = RateLimitConfig()

# Middleware hinzufügen
app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=rate_limiter,
    config=rate_limit_config,
)
```python

### 6. Burst Protection

**Zusätzlicher Schutz gegen Burst-Angriffe:**

```python
class BurstRateLimiter:
    """Rate Limiter mit Burst Protection."""
    
    def __init__(
        self,
        redis_url: str,
        burst_limit: int = 10,
        burst_window: int = 1,
        normal_limit: int = 200,
        normal_window: int = 60,
    ):
        self.redis = redis.from_url(redis_url)
        self.burst_limiter = RateLimiter(redis_url, burst_limit, burst_window)
        self.normal_limiter = RateLimiter(redis_url, normal_limit, normal_window)
        
    async def check_rate_limit(self, key: str) -> tuple[bool, dict]:
        """Prüfe sowohl Burst als auch normale Rate Limits."""
        # Erst Burst Limit prüfen
        burst_allowed, burst_info = await self.burst_limiter.check_rate_limit(key)
        if not burst_allowed:
            return False, burst_info
        
        # Dann normales Limit prüfen
        normal_allowed, normal_info = await self.normal_limiter.check_rate_limit(key)
        if not normal_allowed:
            return False, normal_info
        
        # Kombinierte Info
        return True, {
            "limit": normal_info["limit"],
            "remaining": normal_info["remaining"],
            "reset": normal_info["reset"],
            "burst_remaining": burst_info["remaining"],
        }
```python

### 7. Monitoring und Alerting

```python
# app/application/rate_limit_monitoring.py
from prometheus_client import Counter, Gauge

class RateLimitMetrics:
    """Prometheus Metriken für Rate Limiting."""
    
    def __init__(self):
        self.requests_total = Counter(
            "rate_limit_requests_total",
            "Total Requests",
            ["endpoint", "status"]  # status: allowed, blocked
        )
        self.requests_blocked = Counter(
            "rate_limit_requests_blocked_total",
            "Blocked Requests",
            ["endpoint", "key_type"]  # key_type: user, ip
        )
        self.current_rate = Gauge(
            "rate_limit_current_rate",
            "Current Request Rate",
            ["endpoint"]
        )
    
    def record_request(self, endpoint: str, allowed: bool, key_type: str):
        """Zeichne Request auf."""
        status = "allowed" if allowed else "blocked"
        self.requests_total.labels(endpoint=endpoint, status=status).inc()
        
        if not allowed:
            self.requests_blocked.labels(endpoint=endpoint, key_type=key_type).inc()

# Integration in Middleware
class RateLimitMiddleware:
    def __init__(self, app, rate_limiter, config, metrics: RateLimitMetrics):
        # ... bestehende Initialisierung
        self.metrics = metrics
        
    async def __call__(self, request, call_next):
        # ... bestehende Logik
        
        # Metriken aufzeichnen
        endpoint = request.url.path
        key_type = "user" if getattr(request.state, "user_sub", None) else "ip"
        self.metrics.record_request(endpoint, allowed, key_type)
        
        return response
```python

### 8. Konfiguration per Environment

```yaml
# .env
# Rate Limiting Konfiguration
RATE_LIMIT_DEFAULT_LIMIT=200
RATE_LIMIT_DEFAULT_WINDOW=60
RATE_LIMIT_BURST_LIMIT=10
RATE_LIMIT_BURST_WINDOW=1
RATE_LIMIT_AUTHENTICATED_MULTIPLIER=2.0

# Endpunkt-spezifische Limits (JSON)
RATE_LIMIT_ENDPOINTS='{
  "/api/health": {"limit": 60, "window": 60},
  "/api/v1/auth/oidc/discovery": {"limit": 100, "window": 60},
  "/api/v1/auth/oidc/token": {"limit": 100, "window": 60},
  "/api/v1/export/*/calendar.ics": {"limit": 60, "window": 60}
}'
```yaml

### 9. Frontend Integration

**Handling von HTTP 429:**

```typescript
// services/frontend/src/composables/useRateLimit.ts
import { ref } from 'vue'

export function useRateLimit() {
  const rateLimitInfo = ref<{
    limit: number
    remaining: number
    reset: number
    retryAfter?: number
  } | null>(null)
  
  const updateRateLimit = (response: Response) => {
    rateLimitInfo.value = {
      limit: parseInt(response.headers.get('X-RateLimit-Limit') || '0'),
      remaining: parseInt(response.headers.get('X-RateLimit-Remaining') || '0'),
      reset: parseInt(response.headers.get('X-RateLimit-Reset') || '0'),
    }
    
    if (response.status === 429) {
      rateLimitInfo.value.retryAfter = parseInt(response.headers.get('Retry-After') || '0')
    }
  }
  
  const isRateLimited = () => {
    return rateLimitInfo.value?.remaining === 0
  }
  
  const getRetryAfterMessage = () => {
    if (rateLimitInfo.value?.retryAfter) {
      return `Bitte warten Sie ${rateLimitInfo.value.retryAfter} Sekunden`
    }
    return ''
  }
  
  return {
    rateLimitInfo,
    updateRateLimit,
    isRateLimited,
    getRetryAfterMessage,
  }
}
```typescript

**Verwendung in Komponenten:**

```vue
<!-- services/frontend/src/components/RateLimitWarning.vue -->
<template>
  <div v-if="isRateLimited()" class="alert alert-warning">
    <i class="fas fa-exclamation-triangle"></i>
    Zu viele Anfragen. {{ getRetryAfterMessage() }}
  </div>
</template>

<script setup>
import { useRateLimit } from '@/composables/useRateLimit'

const { isRateLimited, getRetryAfterMessage } = useRateLimit()
</script>
```vue

## Risks / Trade-offs

| Risiko | Auswirkung | Mitigation |
|--------|------------|------------|
| **Redis Overhead** | Zusätzliche Last auf Redis | Dedizierte Redis-Instanz für Rate Limiting |
| **False Positives** | Legitime Nutzer werden blockiert | Konfigurierbare Limits, Whitelisting |
| **Performance Impact** | Zusätzliche Latenz durch Redis-Calls | Connection Pooling, Pipeline-Optimierung |
| **Complexity** | Erhöhte Komplexität | Klare Abstraktion, gute Dokumentation |
| **Distributed Attacks** | Rate Limiting funktioniert nicht bei verteilten IPs | IP-Blocking auf Netzwerkebene |

## Migration Plan

### Phase 1: Infrastruktur (1 Tag)
1. RateLimiter Klasse implementieren
2. RateLimitConfig erstellen
3. Redis-Verbindung testen

### Phase 2: Middleware (1 Tag)
1. RateLimitMiddleware implementieren
2. In FastAPI integrieren
3. Header in Responses hinzufügen

### Phase 3: Konfiguration (1 Tag)
1. Endpunkt-spezifische Limits definieren
2. Environment-Konfiguration hinzufügen
3. Default-Werte setzen

### Phase 4: Testing (2 Tage)
1. Unit Tests für Rate Limiter
2. Integration Tests mit FastAPI
3. Performance Tests
4. Load Testing

### Phase 5: Rollout (1 Tag)
1. Staging Deployment
2. Monitoring einrichten
3. Alerting konfigurieren
4. Produktion Rollout

**Rollback:**
- Rate Limiting kann über Feature-Flag deaktiviert werden
- Redis-Keys haben TTL und werden automatisch gelöscht
- Keine Datenbank-Änderungen nötig

## Open Questions

1. Sollten verschiedene Limits für verschiedene Nutzerrollen gelten?
   - **Empfehlung:** Nein, nur authentifiziert vs. unauthentifiziert

2. Sollten Rate-Limit-Verstöße in Audit-Logs erfasst werden?
   - **Empfehlung:** Ja, für Security Monitoring

3. Sollten Rate Limits dynamisch basierend auf Server-Last angepasst werden?
   - **Empfehlung:** Nein, statische Konfiguration reicht

4. Sollten Rate Limits für interne Requests (Service-to-Service) gelten?
   - **Empfehlung:** Nein, nur für externe Requests

5. Wie mit API-Gateways umgehen?
   - **Empfehlung:** Rate Limiting auf Application-Ebene reicht

