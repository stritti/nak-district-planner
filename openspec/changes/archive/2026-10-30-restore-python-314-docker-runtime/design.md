## Verified cause
Main's earlier Dockerfile `python:3.14.8-slim` built successfully in [workflow 40099089385](https://github.com/stritti/nak-district-planner/actions/runs/40099089385). After an unrelated Python bump to `python:3.15.0-slim`, the backend build in [40109606166](https://github.com/stritti/nak-district-planner/actions/runs/40109606166) failed during `uv sync --frozen --no-dev --no-install-project` building `httptools==0.8.0` from source: `gcc: No such file or directory`. The backup [restore drill 40109606152](https://github.com/stritti/nak-district-planner/actions/runs/40109606152) failed in the same build step.

## Decision
Revert one Dockerfile base line to previously verified Python 3.14.8-slim. This matches existing backend CI's Python 3.14 contract and keeps the runtime free of a build toolchain. Installing GCC into the production image would increase its attack surface and still leave unverified Python 3.15 C-extension compatibility.

## Regression verification
- Run the unchanged Docker image build with frozen uv dependencies.
- Run the encrypted backup restore drill through full completion.
- Require Security Scans and image CVE checks to remain green; no network/cache assumptions in application startup.
- Application and PG-RLS integration tests stay part of the existing backend checks and have a >80% coverage gate.

## Follow-up
Only move to Python 3.15 after the complete pinned dependency graph provides binary wheels or after a separately reviewed multi-stage builder plus the full regression suite passes.
