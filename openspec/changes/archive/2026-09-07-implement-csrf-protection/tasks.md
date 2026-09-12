## Aufgaben für CSRF-Schutz Implementierung

> **Hinweis (2026-09-07):** Dieses `tasks.md` existierte bisher nicht, obwohl das Feature über PR #211 ("fix/csrf-middleware-asgi-crash", ursprünglich in der zugrundeliegenden Feature-PR) bereits implementiert und in `docs/security/csrf-protection.md` dokumentiert ist. Nachträglich gegen den Code-Stand erstellt.

### Kernfunktionalität
- [x] `CSRFTokenService` für Token-Management (`app/application/csrf.py`)
- [x] `CSRFMiddleware` für FastAPI (`app/adapters/api/middleware/csrf.py`)
- [x] Automatische Token-Rotation bei jeder Response
- [x] Token im Header (`X-CSRF-Token`)
- [x] Ausnahme für API-Key-Auth (`X-API-Key`-Header)
- [x] Ausnahmen für GET/HEAD/OPTIONS und `/api/health`
- [x] Frontend: `useCSRF()` Composable (`services/frontend/src/composables/useCSRF.ts`)
- [x] Bugfix: ASGI-Signatur-Crash behoben (PR #211, `775b63f`)

### Bewertung
Kernfunktionalität implementiert und in Produktion (siehe `docs/security/csrf-protection.md`). **Offen:** Browser-seitige Integration (Frontend `useCSRF()` Composable sendet Token im `X-CSRF-Token` Header) muss in E2E-Tests gegen echte Browser-Requests verifiziert werden. Solange dies nicht geschehen ist, gilt der Change als **nicht vollständig abgeschlossen**.
