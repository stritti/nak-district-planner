## ADDED Requirements

### Requirement: Production backend container SHALL install its frozen dependencies
The backend production Docker image SHALL use a supported Python runtime and SHALL install the entire locked, non-development Python dependency set with `uv sync --frozen --no-dev --no-install-project` without relying on unconfigured build compilers.

#### Scenario: Docker image creation
- **WHEN** GitHub Actions builds the backend image from the pinned source and lockfile
- **THEN** the dependency installation and image build succeed

#### Scenario: An unsupported Python base causes missing binary wheels
- **WHEN** the Docker build's locked packages require C-extension wheels unavailable for its Python version
- **THEN** the release and restore quality gates fail rather than publishing the unusable image

#### Scenario: Encrypted backup restore drill
- **WHEN** the isolated restore drill starts backend containers
- **THEN** container construction succeeds and the drill runs to completion
