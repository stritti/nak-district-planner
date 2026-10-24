# Fix backend Docker runtime regression (#742)

**Goal:** Restore reproducible production backend image builds and encrypted backup restore drills.

**Decision:** Revert only the Dockerfile Python base from 3.15.0-slim to known-good 3.14.8-slim, while retaining uv lockfile, non-root runtime and healthchecks.

**Evidence:** Failed Docker build #40109606166 (`httptools` source build lacks gcc); failed restore drill #40109606152; prior successful Docker build #40099089385.

**Implementation:**
- [x] Specify OpenSpec contract and restore pinned known-good base.
- [ ] Run Docker, Restore Drill and Security Scans on PR.
- [ ] Confirm no backend code or database changes.
- [ ] Codex review and merge; main CI verification.

**Risk:** Adding compilers to the runtime image can mask compatibility issues and broaden the attack surface. Require a separately tested upgrade to Python 3.15.
