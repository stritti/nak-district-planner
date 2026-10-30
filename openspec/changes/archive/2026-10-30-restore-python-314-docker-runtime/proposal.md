## Why
Python 3.15.0-slim was adopted before all locked dependencies provided usable 3.15 binary wheels. `httptools==0.8.0` attempted a source build without a compiler in the production runtime image, failing both Docker image validation and the encrypted backup restore drill.

## What Changes
- Restore the previously tested Python 3.14.8 slim runtime base.
- Keep locked dependencies, uv version, non-root runtime user and container healthcheck unchanged.
- Evaluate Python 3.15 compatibility separately when all binary wheels and CI tests support it.

## Capabilities
### Modified Capabilities
- `container-release-quality`: frozen dependency installs must build on the supported runtime base.

## Impact
Backend Dockerfile base image only. No API or database migrations.
