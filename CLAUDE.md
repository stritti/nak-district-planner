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
