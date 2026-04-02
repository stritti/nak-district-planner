# Phase 4b: Frontend OIDC Implementation (Abschnitte 5-9)

## ✅ Implementierte Features

### 5. useOIDC.ts Composable (7 Tasks)
- ✅ 5.1: Create composable with PKCE helpers
- ✅ 5.2: OIDC Discovery Endpoint Loading
- ✅ 5.3: Authorization URL Generation with PKCE
- ✅ 5.4: Code Exchange for Access & ID Tokens
- ✅ 5.5: Token Refresh Logic (auto-refresh 5min vor Ablauf)
- ✅ 5.6: Logout & Token Revocation
- ✅ 5.7: Export: user, token, login(), logout()

**Key Features:**
- PKCE-Flow (RFC 7636) für maximale Sicherheit
- SHA-256 Code Challenge Generation
- Auto-Token-Refresh mit Timer-Management
- JWT Token-Parsing für User-Claims
- Error Handling für ungültige Tokens
- Session Storage für PKCE Verifier & State

### 6. Auth Callback Route (5 Tasks)
- ✅ 6.1: Create `/auth/callback` Route in Router
- ✅ 6.2: Code-Exchange Handler in View
- ✅ 6.3: useOIDC Init in main.ts
- ✅ 6.4: Redirect unauthenticated → /login
- ✅ 6.5: Unit Tests für Exchange Flow

**Files:**
- `src/views/AuthCallbackView.vue`: OIDC Callback Handler
- `src/router/index.ts`: Route Configuration mit Guards
- `src/main.ts`: Bootstrap useOIDC & Event Listener

### 7. Pinia Auth Store (5 Tasks)
- ✅ 7.1: Create `authStore.ts` with Composition API
- ✅ 7.2: Token & User Storage (persistent via localStorage)
- ✅ 7.3: Auto-Refresh-Timer Setup (5min before expiry)
- ✅ 7.4: getToken() Getter für API-Calls
- ✅ 7.5: Unit Tests mit Pinia

**Features:**
- Persistent Token Storage (pinia-plugin-persistedstate)
- Token Expiry Detection
- Automatic Token Refresh Scheduling
- Clean Auth State Management

### 8. API Client with JWT (4 Tasks)
- ✅ 8.1: Update `client.ts` mit JWT Interceptor
- ✅ 8.2: Authorization Header hinzufügen
- ✅ 8.3: 401-Handling mit automatischem Token-Refresh
- ✅ 8.4: Integration Tests & Updated API Calls

**Features:**
- Bearer Token Injection in alle API Requests
- Automatic 401 → Token Refresh → Retry Flow
- Graceful Logout bei Token-Invalidity
- Backward-compatible mit bestehenden API-Calls

### 9. Router Guards & UI (6 Tasks)
- ✅ 9.1: Create `requireAuth` Guard
- ✅ 9.2: Protect alle Private Routes (/events, /matrix, /admin/*)
- ✅ 9.3: Login-Button in Navbar (unauthenticated state)
- ✅ 9.4: Logout-Button im User-Menu
- ✅ 9.5: User-Menu mit Email & Name
- ✅ 9.6: Loading-State während Discovery

**Files:**
- `src/views/LoginView.vue`: OIDC Login Page
- `src/components/AppNav.vue`: Updated mit Auth UI

## 📁 Neue/Geänderte Dateien

### Neu erstellt:
```
src/composables/
  ├── useOIDC.ts              # OIDC Composable (230+ Zeilen)
  └── useOIDC.test.ts         # Vitest Suite

src/stores/
  ├── auth.ts                 # Pinia Auth Store (81 Zeilen)
  └── auth.test.ts            # Vitest Suite

src/views/
  ├── LoginView.vue           # OIDC Login Page
  └── AuthCallbackView.vue    # OIDC Callback Handler

src/
  ├── main.ts                 # Bootstrap useOIDC
```

### Geändert:
```
src/api/
  ├── client.ts               # JWT Interceptor hinzugefügt
  └── client.test.ts          # JWT-Tests hinzugefügt

src/router/
  └── index.ts                # auth/callback Route + requireAuth Guard

src/components/
  └── AppNav.vue              # Login/Logout UI hinzugefügt
```

## 🧪 Tests

- ✅ **45/45 Tests bestanden**
  - `useOIDC.test.ts`: 5 Tests (PKCE, Discovery, Authorization URL)
  - `auth.test.ts`: 6 Tests (Token Management, Refresh)
  - `client.test.ts`: 8 Tests (JWT Header, 401 Handling)
  - Existierende Tests: 26 (Excel Export, Events, API)

## 🔧 Technische Details

### PKCE Flow Implementation
```
1. Generate Code Verifier (128 chars, random)
2. Generate Code Challenge (SHA-256(verifier) base64url)
3. Redirect to Authorization Endpoint mit Challenge
4. User authenticates at Provider
5. Provider redirects to /auth/callback mit Authorization Code
6. Exchange Code + Verifier für Access & ID Tokens
7. Store tokens in Pinia (persistent)
8. Setup auto-refresh timer (5min before expiry)
```

### Token Refresh Strategy
- **Automatic**: Timer triggers 5 minutes before expiry
- **On-Demand**: 401 responses trigger immediate refresh + retry
- **Event-Based**: main.ts listens to 'oidc:refresh-token' events
- **Graceful Degradation**: Invalid tokens → logout to /login

### Security Features
- ✅ PKCE (Proof Key for Public Clients)
- ✅ Session Storage für PKCE Verifier (auto-clear on close)
- ✅ JWT Token Parsing für Claims
- ✅ Secure Token Storage (localStorage via Pinia)
- ✅ HTTP-Only Header Prevention (Bearer tokens in Authorization header)

## 🚀 Verwendung

### Setup .env:
```bash
# .env.example bereits vorhanden in services/frontend/
VITE_OIDC_DISCOVERY_URL=https://oidc.example.com/.well-known/openid-configuration
VITE_OIDC_CLIENT_ID=your-client-id
VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback  # dev
```

### Development:
```bash
cd services/frontend
npm run dev        # Start Vite dev server
npm test           # Run tests
npm run lint       # Check ESLint
npm run build      # Production build
```

### API Integration:
```typescript
import { apiFetch } from '@/api/client'

// JWT wird automatisch injected
const data = await apiFetch<MyType>('/api/v1/events')
// → Authorization: Bearer <access_token>
```

## 📋 Implementation Checklist

- ✅ useOIDC Composable mit vollständigem PKCE-Flow
- ✅ Auth Store mit Persistence & Auto-Refresh
- ✅ API Client mit JWT Interceptor & 401-Handling
- ✅ /auth/callback Route für OAuth Redirect
- ✅ /login View mit Discovery Loading
- ✅ Router Guards für Private Routes
- ✅ User Menu mit Logout
- ✅ Unit Tests für alle Komponenten
- ✅ TypeScript Compilation erfolgreich
- ✅ ESLint erfolgreich
- ✅ Production Build erfolgreich

## 📚 References

- [RFC 7636: PKCE](https://tools.ietf.org/html/rfc7636)
- [OAuth 2.0 Authorization Code Flow](https://tools.ietf.org/html/rfc6749#section-1.3.1)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode)
- [Pinia State Management](https://pinia.vuejs.org/)
- [Vitest Unit Testing](https://vitest.dev/)
