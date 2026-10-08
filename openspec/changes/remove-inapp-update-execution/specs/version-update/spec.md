## ADDED Requirements

### Requirement: Application SHALL NOT execute deployment updates
The application SHALL NOT pull images, rebuild, restart services or run migrations on
its own. It SHALL NOT expose an endpoint, background task, setting or UI control that
triggers a deployment update, and SHALL NOT require a mounted Docker socket.

#### Scenario: Update endpoint is absent
- **WHEN** any client calls `POST /api/v1/system/update`
- **THEN** the API responds with 404 or 405 and no update is started

#### Scenario: Banner offers no update trigger
- **WHEN** an admin sees the update banner
- **THEN** it shows the new version, a release-notes link and the runbook commands using `docker compose -f docker-compose.yml` (build, migrate, `up -d`)
- **AND** it shows no button that starts an update

### Requirement: Version comparison SHALL follow SemVer 2.0 including prereleases
The version check SHALL parse SemVer tags with prerelease identifiers, normalize PEP 440
pre-release versions (`1.0.0rc1` → `1.0.0-rc.1`, `a` → `alpha`, `b` → `beta`), apply
SemVer 2.0 precedence and ignore non-SemVer tags. `update_available` SHALL be true only
if the latest version is strictly newer than the running version.

#### Scenario: Prerelease precedence
- **WHEN** comparing `1.0.0-rc.1`, `1.0.0-rc.2` and `1.0.0`
- **THEN** `1.0.0-rc.1` < `1.0.0-rc.2` < `1.0.0`

#### Scenario: PEP 440 runtime version
- **WHEN** the running version is `1.0.0rc1` and the latest tag is `1.0.0-rc.1`
- **THEN** both are equal and `update_available` is false

#### Scenario: Never offer a downgrade
- **WHEN** the running version is `1.0.0rc1` and the registry contains `0.29.3`
- **THEN** `update_available` is false

### Requirement: Prereleases SHALL only be offered on a prerelease line
Prerelease tags SHALL be considered only when the running version is itself a
prerelease; installations on a stable release SHALL only be offered stable releases.

#### Scenario: Stable 0.x is not offered a release candidate
- **WHEN** the running version is `0.29.3` and the registry contains `1.0.0-rc.1`
- **THEN** no update is offered

#### Scenario: Stable 1.0.0 is not offered 1.1.0-rc.1
- **WHEN** the running version is `1.0.0` and the registry contains `1.1.0-rc.1`
- **THEN** no update is offered

#### Scenario: Release candidate line receives newer candidates and the final release
- **WHEN** the running version is `1.0.0rc1` and the registry contains `1.0.0-rc.2`
- **THEN** `1.0.0-rc.2` is offered, and once `1.0.0` exists, `1.0.0` is offered
