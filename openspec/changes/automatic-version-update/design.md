## Context

The project uses a monorepo with Docker Compose for deployment (5 services: backend, worker, frontend, db, redis). The CI/CD pipeline is fully operational:

- **build.yml** — Builds Docker images on every push (branch/PR) and pushes to `ghcr.io`
- **release.yml** — On push to `main`, analyzes Conventional Commits, bumps SemVer, tags release, builds and publishes versioned images (e.g., `ghcr.io/.../backend:0.4.5`, `...:0.4`, `...:latest`)

Current version is `0.4.5` throughout (`pyproject.toml`, `frontend/package.json`).

There is currently no mechanism for the running application to detect that a newer image exists, nor a way to self-update. Administrators must manually SSH into the server and run `docker compose pull && docker compose up -d`.

## Goals / Non-Goals

**Goals:**
- Provide a version check that compares the running app version against the latest available image tag on `ghcr.io`
- Display an update notification banner to administrators in the web UI
- Provide a **trigger endpoint** that initiates a rolling update of the application containers
- Keep the design secure — the update trigger must not expose arbitrary command execution
- Support two deployment modes: (a) server with Docker socket access, (b) server without Docker access (manual update instructions)

**Non-Goals:**
- Automatic (unsupervised) updates — always requires admin action
- Multi-server / swarm / Kubernetes orchestration — single-host Docker Compose only
- Database migration during update — handled separately via Alembic (outside this scope)
- Update rollback — manual via Docker tags (re-pull previous version tag)
- Update progress/monitoring in the UI — fire-and-forget for MVP
- Frontend-only updates without backend restart

## Decisions

### 1. Version Detection — GitHub Container Registry API

```
┌─────────────┐     GET /v2/.../backend/tags/list     ┌──────────┐
│  Backend     │──────────────────────────────────────▶│ ghcr.io  │
│  (Celery     │◀──────────────────────────────────────│  API     │
│   task)      │     { tags: ["0.4.5", "0.5.0", ...] }│          │
└─────────────┘                                       └──────────┘
```

**Decision:** A Celery periodic task (every 6h) queries the GitHub Container Registry catalog API (`/v2/{repo}/backend/tags/list` and `/v2/{repo}/frontend/tags/list`) to find the latest SemVer tag. The result is cached in Redis (TTL 1h to avoid rate limiting). The `/v1/system/version` endpoint returns both the running version and the cached latest version.

- Registry API is unauthenticated for public packages — no token needed
- Latest version determined by picking SemVer tags, sorting, and returning the highest
- Uses existing `httpx` dependency (already in `pyproject.toml`)

**Alternative considered:** GitHub Releases API — rejected because it requires a GitHub token and has stricter rate limits. The Container Registry tag API is simpler and already public.

**Alternative considered:** Polling the GitHub repo's latest release — same auth/rate-limit problem.

### 2. Deployment Modes — How "Update" Works

Two modes controlled by the `UPDATE_MODE` env var:

| Mode | Value | Description |
|---|---|---|
| **Automatic** | `docker-socket` | Backend container has the Docker socket mounted. Update triggers `docker compose pull` + `docker compose up -d` via subprocess |
| **Manual** | `manual` | Update button shows a dialog with the exact commands to run on the server. No automation. |

**Decision:** Start with both modes. The `docker-socket` mode requires mounting `/var/run/docker.sock` in `docker-compose.override.yml` (dev) or a production Compose override. The `manual` mode is the safe default.

**Alternative considered:** SSH from container to host — rejected. Docker socket is simpler and avoids managing SSH keys inside the container.

### 3. Update Endpoint — `POST /api/v1/system/update`

```python
@router.post("/system/update")
async def trigger_update(admin: User = Depends(require_admin)):
    if settings.update_mode == "manual":
        return {
            "status": "manual",
            "instructions": [
                "cd /opt/nak-district-planner",
                "docker compose pull",
                "docker compose up -d"
            ]
        }
    
    # docker-socket mode: fire Celery task
    trigger_docker_update.delay()
    return {"status": "started", "mode": "docker-socket"}
```

**Decision:** In `docker-socket` mode, the actual pull/restart runs as a Celery task (async, so the HTTP request doesn't hang). The task uses `subprocess.run()` to execute `docker compose pull` and `docker compose up -d`.

### 4. Security — No Arbitrary Command Execution

- The update endpoint is **admin-only** (RBAC `ADMIN` role)
- The subprocess in `docker-socket` mode runs fixed commands only — no user-supplied arguments
- In `manual` mode, only display instructions — no execution happens server-side

### 5. UI — Update Banner

```
┌─────────────────────────────────────────────────────────┐
│  ● New version 0.5.0 available   [View Release Notes]   │
│  Release: v0.5.0 · 2026-06-10                            │
│  [Update Now ▾]                                          │
│  ├─ Automatic (pull & restart)                           │
│  └─ Show manual instructions                             │
└─────────────────────────────────────────────────────────┘
```

**Decision:** A dismissible info banner at the top of admin pages (similar to Tailwind `bg-blue-50` banner). Uses a Pinia store that polls `/api/v1/system/version` on mount and whenever the update is triggered.

### 6. Running Version Source

The running version comes from the application itself:
- Backend: `importlib.metadata.version("nak-district-planner-backend")` or a `VERSION` constant
- Frontend: `import.meta.env.PACKAGE_VERSION` (injected by Vite)

**Decision:** Expose the backend version via a settings field. The frontend reads its own version from `package.json` and sends it to the version endpoint for cross-checking.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **Docker socket access** — container with Docker socket has root-equivalent host access | Restrict to only `docker compose` commands; the `manual` mode is the safer default. Document the security implications prominently. |
| **Update during active use** — restarting services drops in-flight requests | Send a `GET /health` check first; the frontend polls readiness after restart and shows "Update in progress…" |
| **ghcr.io rate limiting** — anonymous pulls are rate-limited by IP | Cache version check results (Redis, 1h TTL). Only the version check uses the tags API (not pulls). |
| **Version skew** — frontend and backend versions could differ | Show both versions in the banner: "Backend 0.4.5 → 0.5.0, Frontend 0.4.5 → 0.5.0" |
| **Failed update leaves system in inconsistent state** | Document recovery: `docker compose pull && docker compose up -d` manually. The update button is fire-and-forget; admin can always fall back to manual. |
| **Stale cache** — Redis shows outdated latest version for up to 1h after release | Acceptable. Admin can force-refresh via a "Check now" button in the UI that bypasses cache. |

## Open Questions

- Should the update process drain Celery tasks gracefully before restart? → Yes, in `docker-socket` mode, the update task should signal Celery to finish current tasks before restarting.
- Should database migrations run automatically during update? → No, Alembic migrations remain admin-triggered via `docker compose exec backend alembic upgrade head`.
- Should the notification be dismissible permanently or only until the next version? → Dismiss until the next version check finds a newer tag.
