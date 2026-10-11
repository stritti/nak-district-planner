## Why

Issue #472 identifies release hardening gaps in container build contexts, non-root serving, runtime isolation, authentication of cache traffic, standalone IdP configuration, and backup recovery verification. Several related mitigations already exist (PWA API denylist, a subset of healthchecks, separation of DB-owner credentials) and must remain intact.

## What Changes

- Exclude local credentials and artifacts from frontend and backend Docker builds; run Nginx unprivileged on port 8080, aligning all proxy routes, health probes and caching headers.
- Harden the released Compose runtime with no extra capabilities, immutable rootfs, bounded resources and health checks; require authenticated Valkey connections in both Compose variants.
- Enforce non-default runtime secrets during production startup and require explicit HTTPS identity-provider settings.
- Back up cluster-global roles in a separately encrypted archive, then exercise real Alembic migrations and RLS/definer/grant restoration in the isolated Restore Drill.
- Document operational prerequisites, compatibility decisions and restore sequence.

## Impact

Production operators must configure a new URL-safe VALKEY_PASSWORD before starting the stack. Unprivileged frontend images listen on 8080 internally; external HTTPS remains unchanged. Restoring backups now requires both the database archive and role metadata archive, plus password rotation. Existing Redis/Valkey client connections must be drained or coordinated during migration.

## Non-goals and rationale

No removal of 'unsafe-inline' in style-src or broad https: img-src without first verifying actual UI dependencies and introducing a CSP migration. PostgreSQL, Valkey and the reverse proxy retain their required writable volumes and process capabilities where container-specific needs have not been validated. The existing PWA denylist and database-owner isolation are preserved without duplication.
