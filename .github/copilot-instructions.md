# Copilot Instructions

## Project Overview

**NAK Bezirksplaner** is a planning tool for worship services and events in NAK (Neuapostolische Kirche / New Apostolic Church) districts. It manages congregations, appointments, and service assignments, and exports calendars as ICS feeds.

The specification and domain language use German. Key terms:

- **Bezirk** = District (root tenant)
- **Gemeinde** = Congregation (belongs to a district)
- **Gottesdienst** = Worship service
- **Dienstzuweisung** = Service assignment
- **LÜCKE** = Gap (missing service assignment, shown in red in the matrix view)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI (async), SQLAlchemy 2.0, Alembic, Celery |
| Database | PostgreSQL 15+ |
| Cache / Queue | Redis |
| Frontend | Vue 3 (Composition API), Vite, Tailwind CSS, Pinia |
| Package managers | **uv** (backend), **bun** (frontend) |
| Infrastructure | Docker & Docker Compose (5 containers) |

---

## Architecture: Hexagonal (Ports & Adapters)

Business logic must **not** depend on FastAPI or SQLAlchemy directly. All repository and calendar connector interfaces are expressed as Abstract Base Classes (ABCs) in `domain/ports/`.

```text
services/backend/app/
  domain/          # Pure Python — no framework imports
    models/        # Domain entities (Event, ServiceAssignment, …)
    ports/         # Abstract interfaces (repositories, CalendarConnector)
  application/     # Use case orchestration (depends only on domain ports)
  adapters/
    api/           # FastAPI routers (inbound adapters)
    db/            # SQLAlchemy repository implementations (outbound adapters)
    calendar/      # Calendar provider implementations (outbound adapters)
```

The **backend** and **worker** containers share the same Docker build context (`services/backend/`) with different start commands — domain logic is never duplicated.

---

## Domain Model

### Tenants

- `District` (Bezirk) — root tenant
- `Congregation` (Gemeinde) — belongs to a district

### CalendarIntegration

External calendar source connected to a congregation or district:

- `type`: `GOOGLE | MICROSOFT | CALDAV | ICS`
- `credentials`: encrypted JSON (OAuth tokens or URL/auth)
- `sync_interval`: minutes between syncs
- `capabilities`: `READ | WRITE | WEBHOOK`

### Event

Core calendar object:

- `source`: `INTERNAL` (created in tool) | `EXTERNAL` (imported)
- `status`: `DRAFT | PUBLISHED`
- `visibility`: `INTERNAL | PUBLIC`
- `audiences`: list of tags (e.g. `"Amtsträger"`, `"Jugend"`)

### ServiceAssignment

Links a service event to a leader:

- `event_id`, `leader_name` (or person ID)
- `status`: `OPEN | ASSIGNED | CONFIRMED`

---

## Use Cases

| ID | Description |
|----|-------------|
| UC-01 | Calendar ingestion via Strategy pattern (OAuth flow → encrypted credentials) |
| UC-02 | Celery background sync with hash-based deduplication |
| UC-03 | District matrix view for service assignment with gap visualization |
| UC-04 | District events distributed to congregations (`status=PUBLISHED` only, via `applicability` list) |
| UC-05 | `/api/v1/export/{token}/calendar.ics` — public tokens anonymize names; internal tokens show full names |

---

## Key Implementation Rules

### Schema & Models

- Use **Pydantic v2** for all schemas — never v1 syntax.
- SQLAlchemy 2.0 style: use `mapped_column`, `Mapped[T]`, and `DeclarativeBase`.

### Security

- API keys and OAuth tokens **must be encrypted** at the service layer (decorator pattern) before storing to DB.
- All `/api/v1/` endpoints require an `X-API-Key` header.
- Never commit secrets or credentials.

### Calendar Sync (UC-02)

- Sync jobs must be **idempotent** — use hash comparison to prevent duplicates.
- Conflict resolution: New → Create, Changed → Update, Deleted → mark `"cancelled"` (configurable).
- UIDs in exported ICS feeds must be **stable over time** so calendar clients don't treat them as new events.

### Frontend Rules

- Use **Tailwind CSS utility classes only** — no custom CSS unless absolutely unavoidable.
- Use the **Composition API** (`<script setup>`) for all Vue components.
- State management via **Pinia** stores.
- Matrix view (UC-03): X-axis = date, Y-axis = congregation. Cell shows `"LÜCKE"` in red when `category=Gottesdienst AND ServiceAssignment=NULL`. Clicking a cell opens a modal to assign a leader.

### Python Code Style

- Line length: **100 characters** (configured in `ruff`).
- Target: **Python 3.11+** syntax.
- Use `async`/`await` throughout (FastAPI async handlers, SQLAlchemy async sessions).

---

## Development Commands

### Full Stack (Docker)

```bash
cp .env.example .env        # First-time setup — fill in secrets
docker compose up -d        # Start all 5 services
docker compose build        # Rebuild after dependency changes
docker compose ps           # Check container status
docker compose logs -f backend  # Stream backend logs
```

### Database Migrations

```bash
# Apply migrations
docker compose run --no-deps --rm backend alembic upgrade head

# Create a new migration after ORM changes
docker compose run --no-deps --rm backend alembic revision --autogenerate -m "short description"
```

### Backend Tests

```bash
# Inside services/backend/
uv run pytest                    # All tests
uv run pytest tests/unit/ -v     # Unit tests only (no DB/network)
uv run pytest tests/integration/ # Integration tests (needs running DB)
```

### Frontend Commands

```bash
# Inside services/frontend/
bun install       # Install dependencies
bun run dev       # Vite dev server (proxies /api → localhost:8000)
bun run build     # Production build
bun run lint      # ESLint
```

---

## Monorepo Structure

```text
nak-district-planner/
├── docker-compose.yml              # Production
├── docker-compose.override.yml     # Dev overrides (hot-reload, exposed ports)
├── .env.example                    # Template — copy to .env
├── services/
│   ├── backend/                    # FastAPI + Celery (Python 3.11)
│   │   ├── app/
│   │   │   ├── main.py             # FastAPI entry point
│   │   │   ├── celery_app.py       # Celery entry point
│   │   │   ├── config.py           # Settings (pydantic-settings)
│   │   │   ├── domain/models/      # Pure Python domain entities
│   │   │   ├── domain/ports/       # ABCs for repos & calendar connectors
│   │   │   ├── application/        # Use case orchestration + Celery tasks
│   │   │   └── adapters/
│   │   │       ├── api/            # FastAPI routers
│   │   │       ├── db/             # SQLAlchemy repository implementations
│   │   │       └── calendar/       # Calendar provider adapters
│   │   ├── alembic/                # Database migrations
│   │   └── tests/
│   │       ├── unit/               # No DB/network required
│   │       └── integration/        # Requires running DB
│   └── frontend/                   # Vue 3 + Tailwind (built with bun)
│       ├── src/
│       │   ├── stores/             # Pinia stores
│       │   ├── views/              # Page components
│       │   └── components/         # Reusable components
│       └── nginx.conf              # SPA routing + API proxy
```

---

## Development Phases

| Phase | Status | Scope |
|-------|--------|-------|
| 1 | ✅ Done | Monorepo scaffold; Docker Compose + PostgreSQL + Redis; FastAPI stub; SQLAlchemy models; `POST /events`, `GET /events` |
| 2 | ⬜ Next | `CalendarConnector` ABC; `iCalConnector` read-only adapter; Celery sync task |
| 3 | ⬜ | Vue 3 + Tailwind + Pinia; event list dashboard; matrix planning view |
| 4 | ⬜ | JWT authentication; API key encryption in DB (service layer decorator) |
