## Decision
Use one isolated Ruff F401 invocation already present in backend CI. Enforce complete coherent domain directories rather than individual cherry-picked files, so newly added modules in those directories are automatically covered. Preserve the prior registration files explicitly. Ruff checks imports as source code without invoking modules, avoiding dependency on initialization side effects.

## Analysis
A code audit identified two unused imports in `app/domain/ports/repositories.py`: `NotificationType` and `EventApprovalStatus`. Neither is referenced in that module and code-search found no consumers importing either symbol from `app.domain.ports.repositories`. Both enum types continue to be exported by their original domain model modules. No other source files are modified.

## Testing
The initial CI gate must reject unused imports in this scope (RED). Removing the two unused symbols then passes the same isolated check (GREEN). The backend integration/RLS tests, total coverage >80%, security checks, OpenSpec and documentation checks must stay green.

## Follow-up
Audit domain/models, application services, infrastructure adapters and tests. Global Ruff F401 ignore remains until full backend audit.
