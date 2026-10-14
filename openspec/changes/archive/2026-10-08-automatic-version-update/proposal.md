## Why

The system already builds Docker images on GitHub and publishes them to `ghcr.io` with SemVer versioning. Administrators currently have no visibility into whether a new version is available — they must manually check the GitHub registry or repository. This means bug fixes, security patches, and new features sit in the registry indefinitely without reaching production.

## What Changes

- New **version check endpoint** on the backend that compares the running application version against the latest available version on `ghcr.io`
- **Admin UI banner/indicator** showing "New version X.Y.Z available" with a link to release notes
- **Update trigger button** that initiates a rolling update of Docker services (backend, worker, frontend) by pulling the latest images and restarting containers
- New **`UPDATE_MODE`** setting to control how updates are performed (manual docker command vs. built-in restart orchestration)
- The existing release pipeline (`release.yml`) is already complete — no changes needed there

## Capabilities

### New Capabilities
- `version-check-and-update`: Periodic check against GitHub Container Registry for newer image versions, display of update availability in the admin UI, and a one-click trigger to pull and restart updated Docker services.

### Modified Capabilities
- *(none – purely additive)*

## Impact

- **Backend** — New API endpoint `GET /api/v1/system/version` returning current and latest version; new `POST /api/v1/system/update` to trigger restart; new Celery task for periodic version check (e.g., every 6h)
- **Frontend** — New admin banner component that checks version endpoint and shows update CTA
- **CI/CD** — A new GitHub Actions workflow `deploy.yml` (or a dispatch endpoint) so the system can trigger a deployment on the server
- **Infrastructure** — Server needs a `DOCKER_COMPOSE_DIR` env var pointing to the project root, and the running container needs access to the Docker socket (or SSH to the host) for update orchestration
