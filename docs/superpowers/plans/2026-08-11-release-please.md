# Release Please Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hand-written release workflow with Release Please manifest mode while keeping one shared version for root, backend, and frontend.

**Architecture:** Release Please owns version calculation, changelog updates, release PRs, Git tags, and GitHub Releases. The release workflow has one manifest-mode Release Please job for `main` pushes and one tag-only Docker publish job for `v*.*.*` tags. Static config files define the package map and initial `0.29.1` manifest state.

**Tech Stack:** GitHub Actions, `googleapis/release-please-action@v4`, Release Please manifest config, Docker Buildx, Docker metadata action, GHCR, Python `pyproject.toml`, Node `package.json`.

## Global Constraints

- Current shared version is `0.29.1` in `package.json`, `services/backend/pyproject.toml`, `services/backend/uv.lock`, and `services/frontend/package.json`.
- Keep shared versioning for root, backend, and frontend; do not introduce independent package versions.
- Do not commit secrets; `RELEASE_PLEASE_TOKEN` must be documented as a GitHub repository secret only.
- Do not keep the old shell-based release logic in parallel with Release Please.
- Do not modify unrelated CI, security, Alembic, or normal branch Docker build workflows.
- `services/backend/uv.lock` is updated via a package-relative extra file entry; do not add a root-level `uv.lock` rule.

---

## File Structure

- Create `release-please-config.json`: Release Please manifest-mode package config with linked versions.
- Create `.release-please-manifest.json`: initial manifest state for all released paths.
- Modify `.github/workflows/release.yml`: replace shell release implementation with Release Please and tag-gated Docker publish.
- Modify `docs/release-process.md`: align documentation with the actual Release Please manifest workflow and required secret.

---

### Task 1: Add Release Please manifest configuration

**Files:**
- Create: `release-please-config.json`
- Create: `.release-please-manifest.json`

**Interfaces:**
- Consumes: Current package names and versions from `package.json`, `services/backend/pyproject.toml`, and `services/frontend/package.json`.
- Produces: Release Please manifest config consumed by `.github/workflows/release.yml`.

- [ ] **Step 1: Create `release-please-config.json`**

Write this exact JSON, including the top-level shared-tag setting and backend `uv.lock` extra-file entry:

```json
{
  "include-component-in-tag": false,
  "packages": {
    ".": {
      "release-type": "node",
      "package-name": "nak-district-planner",
      "component": "root"
    },
    "services/backend": {
      "release-type": "python",
      "package-name": "nak-district-planner-backend",
      "component": "backend",
      "extra-files": [
        {
          "path": "uv.lock",
          "type": "toml",
          "jsonpath": "$.package[?(@.name.value=='nak-district-planner-backend')].version"
        }
      ]
    },
    "services/frontend": {
      "release-type": "node",
      "package-name": "nak-district-planner-frontend",
      "component": "frontend",
      "skip-changelog": true
    }
  },
  "plugins": [
    {
      "type": "linked-versions",
      "groupName": "nak-district-planner",
      "components": ["root", "backend", "frontend"]
    }
  ]
}
```

- [ ] **Step 2: Create `.release-please-manifest.json`**

Write this exact JSON:

```json
{
  ".": "0.29.1",
  "services/backend": "0.29.1",
  "services/frontend": "0.29.1"
}
```

- [ ] **Step 3: Validate JSON syntax**

Run from repository root:

```bash
python -m json.tool release-please-config.json >/tmp/release-please-config.formatted.json
python -m json.tool .release-please-manifest.json >/tmp/release-please-manifest.formatted.json
```

Expected: both commands exit with status `0` and print no errors.

- [ ] **Step 4: Inspect for accidental secret material**

Run:

```bash
git diff -- release-please-config.json .release-please-manifest.json
```

Expected: diff contains only static package names, paths, release types, components, and version `0.29.1`; no token or credential values.

---

### Task 2: Replace the release workflow

**Files:**
- Modify: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `release-please-config.json`, `.release-please-manifest.json`, and `secrets.RELEASE_PLEASE_TOKEN`.
- Produces: Release PRs on `main` pushes and GHCR Docker images on `v*.*.*` tag pushes.

- [ ] **Step 1: Replace `.github/workflows/release.yml`**

Overwrite the file with this workflow:

```yaml
name: Release

on:
  push:
    branches:
      - main
    tags:
      - 'v*.*.*'

permissions:
  contents: write
  issues: write
  packages: write
  pull-requests: write

env:
  NODE_VERSION: '24'

jobs:
  release-please:
    name: Create or Update Release PR
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Run Release Please
        uses: googleapis/release-please-action@v4
        with:
          token: ${{ secrets.RELEASE_PLEASE_TOKEN }}
          config-file: release-please-config.json
          manifest-file: .release-please-manifest.json

  docker-build:
    name: docker-build
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [backend, frontend]
        include:
          - service: backend
            context: services/backend
          - service: frontend
            context: services/frontend

    steps:
      - uses: actions/checkout@v7

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract Docker metadata
        id: meta
        uses: docker/metadata-action@v6
        with:
          images: ghcr.io/${{ github.repository }}/${{ matrix.service }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=raw,value=latest

      - name: Build and push image
        uses: docker/build-push-action@v7
        with:
          context: ${{ matrix.context }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha,scope=${{ matrix.service }}
          cache-to: type=gha,mode=max,scope=${{ matrix.service }}
```

- [ ] **Step 2: Validate workflow syntax with Python YAML parser if available**

Run:

```bash
python - <<'PY'
from pathlib import Path
try:
    import yaml
except ImportError:
    raise SystemExit('PyYAML not installed; skip parser check and inspect YAML manually')
data = yaml.safe_load(Path('.github/workflows/release.yml').read_text())
assert data['name'] == 'Release'
assert data['jobs']['release-please']['if'] == "github.ref == 'refs/heads/main'"
assert data['jobs']['docker-build']['if'] == "startsWith(github.ref, 'refs/tags/v')"
print('workflow yaml ok')
PY
```

Expected: either `workflow yaml ok`, or `PyYAML not installed; skip parser check and inspect YAML manually`. If PyYAML is not installed, continue to Step 3.

- [ ] **Step 3: Inspect workflow diff for removed shell release logic**

Run:

```bash
git diff -- .github/workflows/release.yml
```

Expected:

- Removed steps named `Get latest tag`, `Analyze commits`, `Calculate next version`, `Generate changelog`, `Update versions`, and `Create Release Commit and Tag`.
- Added `googleapis/release-please-action@v4`.
- Docker job is guarded by `startsWith(github.ref, 'refs/tags/v')`.

---

### Task 3: Update release process documentation

**Files:**
- Modify: `docs/release-process.md`

**Interfaces:**
- Consumes: workflow behavior from Task 2 and config files from Task 1.
- Produces: maintainer-facing release documentation.

- [ ] **Step 1: Update the pipeline overview**

Replace the text around the `release.yml` description so it states:

```markdown
### 1. `release.yml` – Release Please + Docker-Veröffentlichung

```text
Push auf main
     │
     ▼
googleapis/release-please-action
     │
     ├─── Kein neuer Commit mit relevantem Typ
     │         → Nichts passiert
     │
     └─── Neuer relevanter Commit erkannt
               │
               ├─── Release-PR existiert noch nicht
               │         → Release-PR wird erstellt / aktualisiert
               │           (CHANGELOG.md + Versions-Bump in Dateien)
               │
               └─── Release-PR wird gemergt
                         → GitHub Release + Git-Tag (z. B. v1.2.3)
                         → Tag-Push startet Docker-Build
                         → Docker-Images mit Versions-Tag veröffentlicht
```

- [ ] **Step 2: Update automatically changed files table**

Ensure the table includes exactly these rows:

```markdown
| Datei | Format |
|-------|--------|
| `package.json` | `"version": "1.2.0"` |
| `services/frontend/package.json` | `"version": "1.2.0"` |
| `services/backend/pyproject.toml` | `version = "1.2.0"` (unter `[project]`) |
| `.release-please-manifest.json` | Aktuelle Release-Please-Versionen pro Pfad |
| `CHANGELOG.md` | Neuer Abschnitt mit allen Änderungen |
```

- [ ] **Step 3: Add required secret documentation**

Add this section before `## Weiterführende Links`:

```markdown
---

## Erforderliches GitHub Secret

Der Workflow erwartet das Repository-Secret `RELEASE_PLEASE_TOKEN`.

Empfohlen ist ein Fine-Grained Personal Access Token mit Schreibrechten für Contents, Pull Requests und Issues. Der normale `GITHUB_TOKEN` sollte nicht für Release Please verwendet werden, weil von ihm erzeugte Tags und Releases nachgelagerte Workflows nicht zuverlässig triggern.

Das Secret darf nicht in Dateien, Logs oder Commits gespeichert werden.
```

- [ ] **Step 4: Remove contradictory manual-trigger wording if present**

Ensure the manual trigger section still says releases are started by pushes to `main`, and does not imply the old shell release implementation is still used.

- [ ] **Step 5: Inspect documentation diff**

Run:

```bash
git diff -- docs/release-process.md
```

Expected: documentation matches manifest-mode Release Please, the required secret is named but no secret value appears.

---

### Task 4: Final verification

**Files:**
- Verify: `release-please-config.json`
- Verify: `.release-please-manifest.json`
- Verify: `.github/workflows/release.yml`
- Verify: `docs/release-process.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: evidence that the release configuration is syntactically valid and aligned with the design.

- [ ] **Step 1: Run JSON syntax checks**

Run:

```bash
python -m json.tool release-please-config.json >/tmp/release-please-config.formatted.json
python -m json.tool .release-please-manifest.json >/tmp/release-please-manifest.formatted.json
```

Expected: both commands exit with status `0`.

- [ ] **Step 2: Run workflow structure check**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('.github/workflows/release.yml').read_text()
required = [
    'googleapis/release-please-action@v4',
    'config-file: release-please-config.json',
    'manifest-file: .release-please-manifest.json',
    "if: github.ref == 'refs/heads/main'",
    "if: startsWith(github.ref, 'refs/tags/v')",
    'docker/build-push-action@v7',
]
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit(f'Missing expected workflow fragments: {missing}')
for forbidden in [
    'Calculate next version',
    'Install changelog generator',
    'Create Release Commit and Tag',
    'git push origin main --follow-tags',
]:
    if forbidden in text:
        raise SystemExit(f'Forbidden old release logic remains: {forbidden}')
print('workflow structure ok')
PY
```

Expected: `workflow structure ok`.

- [ ] **Step 3: Check version consistency**

Run:

```bash
python - <<'PY'
import json
from pathlib import Path

root = json.loads(Path('package.json').read_text())['version']
frontend = json.loads(Path('services/frontend/package.json').read_text())['version']
manifest = json.loads(Path('.release-please-manifest.json').read_text())
backend_version = None
for line in Path('services/backend/pyproject.toml').read_text().splitlines():
    if line.startswith('version = '):
        backend_version = line.split('=', 1)[1].strip().strip('"')
        break

expected = '0.29.1'
values = {
    'package.json': root,
    'services/frontend/package.json': frontend,
    'services/backend/pyproject.toml': backend_version,
    '.release-please-manifest.json:.': manifest.get('.'),
    '.release-please-manifest.json:services/backend': manifest.get('services/backend'),
    '.release-please-manifest.json:services/frontend': manifest.get('services/frontend'),
}
bad = {k: v for k, v in values.items() if v != expected}
if bad:
    raise SystemExit(f'Expected all versions to be {expected}, got {bad}')
print('version consistency ok')
PY
```

Expected: `version consistency ok`.

- [ ] **Step 4: Check no secrets were added**

Run:

```bash
git diff -- release-please-config.json .release-please-manifest.json .github/workflows/release.yml docs/release-process.md docs/superpowers/specs/2026-08-11-release-please-design.md docs/superpowers/plans/2026-08-11-release-please.md
```

Expected: diff may mention `RELEASE_PLEASE_TOKEN` only as a secret name expression (`${{ secrets.RELEASE_PLEASE_TOKEN }}`) or documentation text; no actual token values, passwords, API keys, or credentials.

- [ ] **Step 5: Report verification evidence**

Summarize:

- JSON syntax result.
- Workflow structure result.
- Version consistency result.
- Secret inspection result.
- Any remaining external setup: maintainer must add `RELEASE_PLEASE_TOKEN` in GitHub repository secrets.
