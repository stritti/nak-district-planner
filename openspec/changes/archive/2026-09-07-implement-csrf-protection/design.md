## Context

Der NAK District Planner ist eine Webanwendung mit authentifizierten Nutzern. Ohne CSRF-Schutz können Angreifer durch Cross-Site Request Forgery Nutzer zu unerwünschten Aktionen verleiten.

Aktuell existierende Komponenten:
- FastAPI Backend mit JWT-basierter Authentifizierung
- Vue 3 Frontend mit OIDC-Integration
- Cookie-basierte Session-Storage für OIDC PKCE Verifier

## Goals / Non-Goals

**Goals:**
- Alle state-changing Requests vor CSRF-Angriffen schützen
- Kryptografisch sichere CSRF-Tokens (HMAC-SHA256)
- Minimaler Performance-Impact (< 0.5ms pro Request)
- Kompatibilität mit bestehendem OIDC Flow
- Gute Nutzererfahrung (keine manuellen Token-Refreshes)

**Non-Goals:**
- Schutz vor XSS (ist separates Anliegen)
- Schutz vor Clickjacking (ist separates Anliegen)
- Schutz vor DDoS (ist separates Anliegen)

## Decisions

### 1. CSRF-Schutz Strategie: Double-Submit Pattern

**Begründung:**
- Einfach zu implementieren
- Kompatibel mit modernen SPAs
- Keine Abhängigkeit von Server-Sessions
- Funktioniert mit JWT-basierter Authentifizierung

**Alternativen:**
- Synchronizer Token Pattern: Erfordert Server-Sessions
- SameSite Cookie Attribute: Nicht alle Browser unterstützen es
- Custom Request Headers: Nicht alle Browser erlauben es

### 2. Token Generierung und Validierung

```python
# app/application/csrf.py
import secrets
import hmac
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Optional

class CSRFError(Exception):
    """Raised when CSRF validation fails."""
    pass

class CSRFTokenService:
    """Service für CSRF-Token Generierung und Validierung."""
    
    def __init__(self, secret_key: str, token_lifetime_seconds: int = 86400):
        """
        Args:
            secret_key: Geheimnis für Token-Signierung
            token_lifetime_seconds: Lebensdauer der Tokens (default: 24 Stunden)
        """
        self.secret_key = secret_key.encode()
        self.token_lifetime = timedelta(seconds=token_lifetime_seconds)
        
    def generate_token(self, session_id: Optional[str] = None) -> str:
        """
        Generiere ein neues CSRF-Token.
        
        Args:
            session_id: Optionale Session-ID für Token-Bindung
            
        Returns:
            CSRF-Token als String
        """
        # Generiere zufälligen Token
        random_bytes = secrets.token_bytes(32)
        timestamp = int(datetime.now(UTC).timestamp())
        
        # Erstelle Token-Daten
        token_data = f"{random_bytes.hex()}:{timestamp}"
        if session_id:
            token_data += f":{session_id}"
        
        # Signiere Token
        signature = hmac.new(
            self.secret_key,
            token_data.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        # Kombiniere Daten und Signatur
        return f"{token_data}:{signature}"
    
    def validate_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """
        Validiere ein CSRF-Token.
        
        Args:
            token: CSRF-Token String
            session_id: Optionale Session-ID für Validierung
            
        Returns:
            True wenn Token gültig, False sonst
            
        Raises:
            CSRFError: Wenn Token ungültig ist
        """
        try:
            # Zerlege Token
            parts = token.split(":")
            if len(parts) < 3:
                raise CSRFError("Invalid token format")
            
            # Extrahiere Daten und Signatur
            random_hex = parts[0]
            timestamp_str = parts[1]
            signature = parts[2]
            token_session_id = parts[3] if len(parts) > 3 else None
            
            # Prüfe Timestamp (Lebensdauer)
            timestamp = int(timestamp_str)
            token_time = datetime.fromtimestamp(timestamp, UTC)
            now = datetime.now(UTC)
            
            if now - token_time > self.token_lifetime:
                raise CSRFError("Token expired")
            
            # Prüfe Session-ID
            if session_id and token_session_id != session_id:
                raise CSRFError("Token session mismatch")
            
            # Rekonstruiere Token-Daten
            token_data = f"{random_hex}:{timestamp_str}"
            if token_session_id:
                token_data += f":{token_session_id}"
            
            # Validiere Signatur
            expected_signature = hmac.new(
                self.secret_key,
                token_data.encode(),
                hashlib.sha256,
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                raise CSRFError("Invalid token signature")
            
            return True
            
        except Exception as e:
            raise CSRFError(f"CSRF validation failed: {e}") from e
    
    def get_token_age(self, token: str) -> timedelta:
        """Gib das Alter des Tokens zurück."""
        try:
            parts = token.split(":")
            if len(parts) < 2:
                return timedelta(0)
            
            timestamp = int(parts[1])
            token_time = datetime.fromtimestamp(timestamp, UTC)
            return datetime.now(UTC) - token_time
        except (ValueError, IndexError):
            return timedelta(0)
```python

### 3. CSRF Middleware

```python
# app/adapters/api/middleware/csrf.py
from fastapi import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_403_FORBIDDEN
from typing import Callable, Awaitable, Optional
import logging

logger = logging.getLogger(__name__)

class CSRFMiddleware:
    """FastAPI Middleware für CSRF-Schutz."""
    
    def __init__(
        self,
        app,
        csrf_service: CSRFTokenService,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        exempt_paths: Optional[set[str]] = None,
        exempt_methods: Optional[set[str]] = None,
    ):
        self.app = app
        self.csrf_service = csrf_service
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.exempt_paths = exempt_paths or {"/api/health"}
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}
        
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Skip CSRF für Safe Methods
        if request.method in self.exempt_methods:
            response = await call_next(request)
            return self._add_csrf_cookie(response, request)
        
        # Skip CSRF für exempt paths
        if request.url.path in self.exempt_paths:
            response = await call_next(request)
            return self._add_csrf_cookie(response, request)
        
        # Skip CSRF für API-Key Auth
        if request.headers.get("X-API-Key"):
            response = await call_next(request)
            return response
        
        # Validiere CSRF-Token
        try:
            csrf_token = self._get_csrf_token(request)
            session_id = self._get_session_id(request)
            
            if not csrf_token:
                raise CSRFError("CSRF token missing")
            
            self.csrf_service.validate_token(csrf_token, session_id)
            
        except CSRFError as e:
            logger.warning(f"CSRF validation failed: {e}")
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={"detail": "CSRF validation failed"},
            )
        
        # Führe Request aus
        response = await call_next(request)
        
        # Füge neues CSRF-Token hinzu (Token Rotation)
        return self._add_csrf_cookie(response, request)
        
    def _get_csrf_token(self, request: Request) -> Optional[str]:
        """Extrahiere CSRF-Token aus Header oder Cookie."""
        # Versuche Header
        token = request.headers.get(self.header_name)
        if token:
            return token
        
        # Versuche Cookie
        if hasattr(request, "cookies"):
            return request.cookies.get(self.cookie_name)
        
        return None
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """Extrahiere Session-ID aus Request."""
        # Für JWT-basierte Auth: user_sub als Session-ID
        if hasattr(request.state, "user"):
            return getattr(request.state.user, "sub", None)
        
        # Für Cookie-basierte Session: Session-ID Cookie
        if hasattr(request, "cookies"):
            return request.cookies.get("session_id")
        
        return None
    
    def _add_csrf_cookie(self, response: Response, request: Request) -> Response:
        """Füge neues CSRF-Token als Cookie hinzu."""
        session_id = self._get_session_id(request)
        csrf_token = self.csrf_service.generate_token(session_id)
        
        # Setze Cookie
        response.set_cookie(
            key=self.cookie_name,
            value=csrf_token,
            httponly=True,
            secure=True,  # Nur über HTTPS
            samesite="strict",  # Schutz vor CSRF
            max_age=int(self.csrf_service.token_lifetime.total_seconds()),
            path="/",
        )
        
        return response
```python

### 4. Integration mit FastAPI

```python
# app/main.py
from app.application.csrf import CSRFTokenService
from app.adapters.api.middleware.csrf import CSRFMiddleware
from app.config import settings

# Initialisierung
csrf_service = CSRFTokenService(
    secret_key=settings.secret_key,
    token_lifetime_seconds=86400,  # 24 Stunden
)

# Middleware hinzufügen
app.add_middleware(
    CSRFMiddleware,
    csrf_service=csrf_service,
    cookie_name="csrf_token",
    header_name="X-CSRF-Token",
    exempt_paths={"/api/health", "/api/v1/auth/oidc/discovery", "/api/v1/auth/oidc/token"},
    exempt_methods={"GET", "HEAD", "OPTIONS"},
)
```python

### 5. Frontend Integration

**Vue 3 Composable für CSRF-Token Management:**

```typescript
// services/frontend/src/composables/useCSRF.ts
import { ref, onMounted } from 'vue'
import { useCookies } from '@vueuse/integrations/useCookies'

export function useCSRF() {
  const cookies = useCookies()
  const csrfToken = ref<string>('')
  
  // Lade CSRF-Token aus Cookie
  const loadCSRFToken = () => {
    csrfToken.value = cookies.get('csrf_token') || ''
  }
  
  // Setze CSRF-Token in Request Headers
  const getCSRFHeaders = () => {
    return {
      'X-CSRF-Token': csrfToken.value,
    }
  }
  
  // Prüfe ob CSRF-Token vorhanden
  const hasCSRFToken = () => {
    return !!csrfToken.value
  }
  
  // Initialisierung
  onMounted(() => {
    loadCSRFToken()
  })
  
  return {
    csrfToken,
    loadCSRFToken,
    getCSRFHeaders,
    hasCSRFToken,
  }
}
```typescript

**Verwendung in API-Requests:**

```typescript
// services/frontend/src/api/client.ts
import axios from 'axios'
import { useCSRF } from '@/composables/useCSRF'

const { getCSRFHeaders } = useCSRF()

// Erstelle Axios Instanz mit CSRF-Headers
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    ...getCSRFHeaders(),
  },
})

// Interceptor für CSRF-Token Aktualisierung
apiClient.interceptors.response.use((response) => {
  // Token wird automatisch durch Cookie aktualisiert
  return response
}, (error) => {
  if (error.response?.status === 403 && error.response?.data?.detail === 'CSRF validation failed') {
    // CSRF-Token ungültig, lade neu
    window.location.reload()
  }
  return Promise.reject(error)
})
```typescript

**Verwendung in Komponenten:**

```vue
<!-- services/frontend/src/components/EventForm.vue -->
<template>
  <form @submit.prevent="submitForm">
    <!-- Formular Felder -->
    <button type="submit" :disabled="!hasCSRFToken()">
      Speichern
    </button>
  </form>
</template>

<script setup>
import { useCSRF } from '@/composables/useCSRF'
import { useEvents } from '@/stores/events'

const { hasCSRFToken, getCSRFHeaders } = useCSRF()
const eventStore = useEvents()

const submitForm = async () => {
  try {
    await eventStore.createEvent(
      eventData.value,
      getCSRFHeaders(),
    )
    // Erfolg
  } catch (error) {
    // Fehlerbehandlung
  }
}
</script>
```vue

### 6. OIDC Flow Integration

**CSRF-Schutz für OIDC Flow:**

```python
# app/adapters/api/routers/auth.py
from app.adapters.api.middleware.csrf import CSRFMiddleware
from app.application.csrf import CSRFTokenService

# CSRF für OIDC Endpunkte deaktivieren (wird durch PKCE geschützt)
@router.post("/oidc/token")
async def exchange_oidc_token(body: OIDCTokenExchangeRequest) -> dict:
    # Kein CSRF-Schutz nötig, da PKCE verwendet wird
    # ... bestehende Implementierung
    pass

# CSRF für andere Endpunkte aktiv
@router.post("/me")
async def get_current_user_info(user: AuthenticatedUser) -> UserOut:
    # CSRF-Schutz durch Middleware
    # ... bestehende Implementierung
    pass
```python

### 7. API-Key Auth Ausnahmen

**API-Key Requests sind von CSRF-Schutz ausgenommen:**

```python
# app/adapters/api/middleware/csrf.py
class CSRFMiddleware:
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Skip CSRF für API-Key Auth
        if request.headers.get("X-API-Key"):
            response = await call_next(request)
            return response
        
        # ... Rest der Implementierung
```python

### 8. Security Considerations

**Schutzmaßnahmen:**

1. **HTTP-Only Cookies:**
   - CSRF-Token wird in HTTP-Only Cookie gespeichert
   - Verhindert Zugriff durch JavaScript (XSS-Schutz)

2. **SameSite Attribute:**
   - `SameSite=Strict` verhindert Senden des Cookies in Cross-Site Requests
   - Zusätzlicher Schutz gegen CSRF

3. **Secure Attribute:**
   - Cookie wird nur über HTTPS gesendet
   - Verhindert MITM-Angriffe

4. **Token Rotation:**
   - Neues Token wird bei jedem Response gesetzt
   - Altes Token wird nach 24 Stunden ungültig

5. **HMAC-Signierung:**
   - Tokens sind kryptografisch signiert
   - Manipulation wird erkannt

6. **Session-Bindung:**
   - Tokens sind an Session-ID gebunden
   - Verhindert Token-Diebstahl

## Risks / Trade-offs

| Risiko | Auswirkung | Mitigation |
|--------|------------|------------|
| **Performance Impact** | Zusätzliche Latenz durch Token-Validierung | Optimierte Implementierung, Caching |
| **Complexity** | Erhöhte Komplexität für Frontend | Klare Abstraktion, gute Dokumentation |
| **User Experience** | Nutzer müssen Seite neu laden bei Token-Ablauf | Automatische Token-Rotation |
| **Compatibility** | Probleme mit bestimmten Browsern | Feature Detection, Fallbacks |
| **False Positives** | Legitime Requests werden blockiert | Gute Fehlerbehandlung, Logging |

## Migration Plan

### Phase 1: Backend Infrastruktur (1 Tag)
1. CSRFTokenService implementieren
2. CSRFMiddleware implementieren
3. In FastAPI integrieren
4. Konfiguration hinzufügen

### Phase 2: Frontend Integration (1 Tag)
1. useCSRF Composable erstellen
2. Axios Interceptors konfigurieren
3. API-Client anpassen

### Phase 3: Testing (2 Tage)
1. Unit Tests für CSRF-Service
2. Integration Tests mit FastAPI
3. Frontend Tests
4. End-to-End Tests

### Phase 4: Rollout (1 Tag)
1. Staging Deployment
2. Monitoring einrichten
3. Fehlerbehandlung testen
4. Produktion Rollout

**Rollback:**
- CSRF-Schutz kann über Feature-Flag deaktiviert werden
- Keine Datenbank-Änderungen nötig
- Frontend kann zu alter Version zurückgerollt werden

## Open Questions

1. Sollten CSRF-Tokens pro Endpunkt oder global sein?
   - **Empfehlung:** Global (ein Token für alle Endpunkte)

2. Sollten CSRF-Tokens bei jedem Request rotiert werden?
   - **Empfehlung:** Nein, nur bei Response (reduziert Komplexität)

3. Sollten CSRF-Tokens für GET Requests gesetzt werden?
   - **Empfehlung:** Ja, für bessere Nutzererfahrung

4. Wie mit Mobile Apps umgehen?
   - **Empfehlung:** Mobile Apps verwenden API-Key Auth (ausgenommen)

5. Sollten CSRF-Fehler in Audit-Logs erfasst werden?
   - **Empfehlung:** Ja, für Security Monitoring

