# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**Phase 1 — Monorepo scaffolding complete.** The directory structure and all Docker/config files are in place. Next: implement SQLAlchemy models and the first FastAPI endpoints.

The spec is written in German (NAK = Neuapostolische Kirche / New Apostolic Church).

## Monorepo Structure

```text
nak-district-planner/
├── docker-compose.yml              # 5 Services: backend, worker, frontend, db, redis
├── docker-compose.override.yml     # Dev-Overrides (Hot-Reload, exposed ports)
├── .env.example                    # Template — copy to .env and fill in values
├── services/
│   ├── backend/                    # FastAPI + Celery (shared Python codebase)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── app/
│   │   │   ├── main.py             # FastAPI entry point
│   │   │   ├── celery_app.py       # Celery entry point
│   │   │   ├── domain/
│   │   │   │   ├── models/         # Pure Python domain entities
│   │   │   │   └── ports/          # ABCs for repositories & calendar connectors
│   │   │   ├── application/        # Use case orchestration + Celery tasks
│   │   │   └── adapters/
│   │   │       ├── api/            # FastAPI routers (inbound)
│   │   │       ├── db/             # SQLAlchemy repository implementations (outbound)
│   │   │       └── calendar/       # Calendar provider adapters (outbound)
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   └── frontend/                   # Vue 3 + bun → nginx:alpine
│       ├── Dockerfile              # Multi-stage: bun build → nginx:alpine
│       ├── nginx.conf
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── main.ts
│           ├── App.vue
│           ├── stores/             # Pinia stores
│           ├── views/
│           └── components/
```

## Tech Stack

**Backend:** Python 3.11+, FastAPI (async), SQLAlchemy 2.0, PostgreSQL 15+, Redis + Celery — managed with **uv**
**Frontend:** Vue.js 3 (Composition API), Vite, Tailwind CSS, Pinia — built with **bun**
**Infrastructure:** Docker & Docker Compose (5 containers)

## Commands

```bash
# First-time setup
cp .env.example .env               # Fill in values

# Run everything
docker compose up -d               # Start all 5 services
docker compose build               # Rebuild images after dependency changes
docker compose ps                  # Check service status
docker compose logs -f backend     # Follow backend logs

# Backend development (inside services/backend/)
uv run pytest                      # Run all tests
uv run pytest tests/unit/ -v       # Unit tests only (no DB/network needed)
uv run pytest tests/integration/   # Integration tests (needs running DB)

# Frontend development (inside services/frontend/)
bun install                        # Install dependencies
bun run dev                        # Vite dev server (proxies /api → localhost:8000)
bun run build                      # Production build
bun run lint                       # ESLint
```

## Architecture: Hexagonal (Ports & Adapters)

Business logic must **not** depend on FastAPI or SQLAlchemy directly. Use Abstract Base Classes for all repository and calendar connector interfaces.

```text
app/
  domain/        # Pure Python — no framework imports
    models/      # Domain entities (Event, ServiceAssignment, etc.)
    ports/       # Abstract interfaces (repositories, CalendarConnector)
  application/   # Use case orchestration (depends only on domain ports)
  adapters/
    api/         # FastAPI routers (inbound)
    db/          # SQLAlchemy repository implementations (outbound)
    calendar/    # Calendar provider implementations (outbound)
```

**Backend + Worker share the same Docker build context** (`services/backend/`). They are separate containers with different start commands — this avoids duplicating domain logic.

## Domain Model

**Tenants:**
- `District` (Bezirk) — root tenant
- `Congregation` (Gemeinde) — belongs to a district

**CalendarIntegration** — external calendar source:
- `type`: GOOGLE | MICROSOFT | CALDAV | ICS
- `credentials`: encrypted JSON (OAuth tokens or URL/auth)
- `sync_interval`: minutes
- `capabilities`: READ | WRITE | WEBHOOK

**Event** — core calendar object:
- `source`: INTERNAL (created in tool) | EXTERNAL (imported)
- `status`: DRAFT | PUBLISHED
- `visibility`: INTERNAL | PUBLIC
- `audiences`: list of tags (e.g. "Amtsträger", "Jugend")

**ServiceAssignment** — links a service event to a leader:
- `event_id`, `leader_name` (or person ID)
- `status`: OPEN | ASSIGNED | CONFIRMED

## Key Implementation Rules

**Sync idempotency:** Calendar sync jobs must use hash comparison to prevent duplicates. On conflict: Neu→Create, Geändert→Update, Gelöscht→mark "cancelled" (configurable).

**iCal stability:** UIDs in exported ICS feeds must be stable over time so calendar apps don't treat them as new events.

**Credential encryption:** API keys and OAuth tokens must be encrypted at the service layer (decorator pattern) before storing to DB.

**Pydantic v2** for all schemas — not v1.

**Tailwind classes only** — no custom CSS unless unavoidable.

**Matrix view** (UC-03): X-axis = date, Y-axis = congregation. Cell shows "LÜCKE" (gap, red) when `category=Gottesdienst AND ServiceAssignment=NULL`. Click → modal to assign leader.

## Use Cases Summary

- **UC-01:** Calendar ingestion via Strategy pattern (OAuth flow → encrypted credentials)
- **UC-02:** Celery background sync with hash-based deduplication
- **UC-03:** District matrix view for service assignment with gap visualization
- **UC-04:** District events distributed to congregations (only `status=PUBLISHED`, via `applicability` list)
- **UC-05:** `/api/v1/export/{token}/calendar.ics` — public tokens anonymize `ServiceAssignment` names; internal tokens show full names

## Development Phases

1. **Phase 1 (MVP):** ✅ Monorepo scaffold; Docker Compose + PostgreSQL + Redis; FastAPI stub; implement SQLAlchemy models + `POST /events`, `GET /events` with district/congregation filters
2. **Phase 2:** `CalendarConnector` ABC; `iCalConnector` read-only adapter; Celery sync task
3. **Phase 3:** Vue 3 + Tailwind + Pinia scaffolding; event list dashboard; matrix planning view
4. **Phase 4:** JWT authentication; API key encryption in DB (service layer decorator)

---

## Security Guidelines for AI Agents

### Security-First Development Principles

When working on this codebase, **ALWAYS** prioritize security considerations:

1. **Never commit secrets** - API keys, passwords, tokens, or any sensitive data must NEVER be committed to the repository
2. **Validate all inputs** - Use Pydantic v2 models for all API inputs, validate before processing
3. **Principle of Least Privilege** - Grant minimum necessary permissions for all operations
4. **Defense in Depth** - Implement multiple layers of security controls
5. **Fail Securely** - Default to denying access rather than allowing it

### Critical Security Areas

#### Authentication & Authorization
- **OIDC Integration:** Use the existing `OIDCAdapter` class for all authentication
- **Token Validation:** Always validate JWT tokens with signature, issuer, audience, and expiration checks
- **RBAC Enforcement:** Use `has_role_in_district()` and `has_role_in_congregation()` for all authorization checks
- **Membership Gate:** Always verify user has appropriate membership before allowing access to resources
- **Superadmin Check:** Use `user.is_superadmin` for system-wide operations

**Required Pattern:**
```python
# ALWAYS check permissions before any write operation
from app.adapters.auth.permissions import assert_has_role_in_district, PermissionError
from app.domain.models.role import Role

try:
    assert_has_role_in_district(auth_context, Role.DISTRICT_ADMIN, district_id)
except PermissionError as e:
    raise HTTPException(status_code=403, detail=str(e))
```

#### Data Protection
- **Credential Encryption:** Use `app.application.crypto.encrypt_credentials()` and `decrypt_credentials()` for all sensitive data
- **Never log sensitive data:** Avoid logging tokens, passwords, API keys, or personal information
- **HTTPS Only:** Ensure all production deployments use HTTPS (configured at reverse proxy)
- **Secure Headers:** Implement security headers in production (CSP, HSTS, X-Frame-Options, etc.)

**Required Pattern:**
```python
# ALWAYS encrypt credentials before storage
from app.application.crypto import encrypt_credentials, decrypt_credentials

# Encrypt before saving to database
encrypted = encrypt_credentials({"api_key": "secret-value", "url": "https://..."})

# Decrypt when needed
decrypted = decrypt_credentials(encrypted)
```

#### API Security
- **Input Validation:** Use Pydantic v2 models for all request bodies, query parameters, and path parameters
- **Rate Limiting:** Implement rate limiting for all public endpoints (see `docs/security-analysis.md`)
- **CSRF Protection:** Add CSRF tokens for state-changing requests in web interfaces
- **Error Handling:** Never expose stack traces or sensitive error details in production

**Required Pattern:**
```python
# ALWAYS use Pydantic models for input validation
from pydantic import BaseModel, Field

class EventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    district_id: uuid.UUID
    # All fields are automatically validated
```

#### Tenant Isolation (Multi-Tenancy)
- **Scope Validation:** Always verify user has access to the requested district/congregation
- **Cross-Tenant Prevention:** Never allow users to access data from other tenants
- **Row-Level Security:** Consider PostgreSQL RLS for database-level tenant isolation

**Required Pattern:**
```python
# ALWAYS validate tenant access
from app.adapters.auth.permissions import has_role_in_district

if not has_role_in_district(auth_context, Role.VIEWER, district_id):
    raise HTTPException(status_code=403, detail="Access denied")
```

### Security Code Review Checklist

Before any merge, verify the following security aspects:

- [ ] **No secrets committed** - Check for passwords, API keys, tokens in code
- [ ] **Input validation present** - All API endpoints have Pydantic models
- [ ] **Authorization checks** - All write operations have permission checks
- [ ] **Tenant isolation** - Users cannot access other tenants' data
- [ ] **Sensitive data encrypted** - Credentials and tokens are encrypted at rest
- [ ] **Error handling secure** - No sensitive data in error responses
- [ ] **Logging safe** - No sensitive data in logs
- [ ] **Dependencies scanned** - New dependencies have been security-reviewed

### Security Testing Requirements

All security-related changes must include:

1. **Unit Tests** for new security features
2. **Integration Tests** for authentication/authorization flows
3. **Negative Tests** - Verify unauthorized access is properly denied
4. **Edge Case Tests** - Test with malformed inputs, expired tokens, etc.

**Example Test:**
```python
# Test that unauthorized access is denied
def test_create_event_without_permission():
    # Setup: user without DISTRICT_ADMIN role
    user = create_test_user(role=Role.VIEWER)
    
    # Attempt to create event
    response = client.post("/api/v1/events", json={...}, headers={"Authorization": f"Bearer {user.token}"})
    
    # Verify access denied
    assert response.status_code == 403
    assert "Access denied" in response.json()["detail"]
```

### Security Documentation

**Mandatory Reading for Security Work:**
- `docs/security-baseline.md` - Security baseline requirements
- `docs/security-analysis.md` - Comprehensive security analysis with threat modeling
- `docs/roles.md` - Role model and permission matrix
- `docs/approval-workflow.md` - User onboarding and approval workflow

**Reference Documents:**
- `docs/production-runbook.md` - Production security procedures
- `.github/workflows/security.yml` - Automated security scanning workflow

### Security Incident Response

If you detect or suspect a security vulnerability:

1. **STOP** - Do not commit or push the code
2. **ISOLATE** - Contain the potential issue
3. **REPORT** - Immediately notify the security team
4. **DOCUMENT** - Record all observations and steps taken

**Contact:** security@nak-district-planner.example

### Prohibited Actions

**NEVER do the following:**
- ❌ Commit secrets, passwords, or API keys to the repository
- ❌ Disable security checks for "convenience" during development
- ❌ Use `eval()` or similar dangerous functions with user input
- ❌ Store sensitive data in plaintext
- ❌ Log sensitive information (tokens, passwords, personal data)
- ❌ Bypass authentication/authorization checks
- ❌ Use hardcoded credentials or secrets
- ❌ Disable HTTPS in production
- ❌ Expose internal ports in production (8000, 5432, 6379)
- ❌ Use `sudo` or root privileges unnecessarily in Docker containers

### Security Tools & Commands

```bash
# Run security scans locally
make lint                          # Linting checks

# Backend security tests
docker compose run --no-deps --rm backend pytest tests/unit/test_auth_permissions_jwt_claims.py -v
docker compose run --no-deps --rm backend pytest tests/unit/test_oidc_adapter.py -v
docker compose run --no-deps --rm backend pytest tests/unit/test_crypto.py -v

# Dependency security scans
uv export --format requirements-txt --no-dev --no-emit-project -o /tmp/requirements.txt
pip-audit -r /tmp/requirements.txt

cd services/frontend
bun audit --level moderate

# CodeQL analysis (requires GitHub Actions or local setup)
codeql database create --language python .
codeql analyze --format=sarif --output=results.sarif .
```

### Security-Related Files & Directories

**Backend Security Components:**
- `services/backend/app/adapters/auth/` - Authentication and authorization modules
- `services/backend/app/application/crypto.py` - Credential encryption
- `services/backend/app/config.py` - Security configuration
- `services/backend/tests/unit/test_*auth*.py` - Authentication tests
- `services/backend/tests/unit/test_*crypto*.py` - Encryption tests

**Frontend Security Components:**
- `services/frontend/src/composables/useOIDC.ts` - OIDC authentication
- `services/frontend/src/stores/auth.ts` - Auth state management

**Infrastructure Security:**
- `docker-compose.yml` - Production configuration (no exposed ports)
- `docker-compose.override.yml` - Development configuration (exposed ports for debugging)
- `.github/workflows/security.yml` - Automated security scanning

---

## Quick Reference: Security Decision Tree

```
Is this a security-sensitive change?
    │
    ├── Yes
    │   │
    │   ├── Does it involve authentication/authorization?
    │   │   │
    │   │   ├── Yes → Review docs/roles.md and test with multiple role levels
    │   │   │
    │   │   └── No
    │   │       │
    │   │       ├── Does it handle sensitive data?
    │   │       │   │
    │   │       │   ├── Yes → Use encryption (crypto.py) and secure storage
    │   │       │   │
    │   │       │   └── No
    │   │       │       │
    │   │       │       ├── Does it accept user input?
    │   │       │       │   │
    │   │       │       │   ├── Yes → Validate with Pydantic, sanitize, escape
    │   │       │       │   │
    │   │       │       │   └── No → Proceed with standard review
    │   │       │       │
    │   │       └── Consult docs/security-analysis.md for threat modeling
    │   │
    └── No → Standard code review applies
```
