# Contributing to NAK District Planner

Vielen Dank für Beiträge zum NAK District Planner. Bitte zuerst die [Dokumentationslandkarte](../docs/documentation-map.md), [Roadmap](../docs/roadmap.md) und [Engineering Standards](../docs/development/engineering-standards.md) lesen.

## Änderungen vorbereiten

1. Für neue Features oder fachliche Änderungen zuerst einen [OpenSpec-Change](../openspec/changes/) mit Proposal, Design, Tasks und passenden Spec-Deltas erstellen; bestehende implementierte Regeln sind unter [openspec/specs](../openspec/specs/) beschrieben.
2. Issues und offene Pull Requests auf Überschneidungen prüfen. Ein PR soll einen klar abgegrenzten Gegenstand behandeln.
3. Backend: Ports-and-Adapters, typisierte Schnittstellen, sichere Tenant-/RBAC-Grenzen. Frontend: vorhandene Vue-Patterns wiederverwenden. Datenschutz und Least Privilege beachten.
4. Änderungen mit positiven, negativen und Randfall-Tests absichern. **Coverage-Gates über 80 % nicht abschwächen oder Production-Code aus der Messung ausschließen.**
5. Bei fachlichen Änderungen OpenSpec-Baseline, Benutzer-Doku, Tests und Runbook zusammen aktualisieren. OpenSpec-Changes erst nach erfolgreicher Implementierung archivieren.

## Lokal prüfen

```bash
# Dokumentation (Repository-Root)
bun install --frozen-lockfile
bun run docs:build

# Backend (separat)
cd services/backend
uv run pytest tests/unit/
uv run pytest tests/integration/
cd ../frontend
bun install --frozen-lockfile
bun run test
bun run lint
bun run build
```

Integrationstests benötigen die in der [Entwicklerdokumentation](../README.md#entwicklung) beschriebene Umgebung. Weitere verbindliche Qualitätsregeln: [Coverage-Strategie](../docs/development/coverage-strategy.md). OpenSpec gegen das verwendete CLI/CI prüfen: `openspec validate --all --strict --no-interactive`.

## Pull Requests

Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`) nutzen, Änderungen und Nachweise beschreiben, CI prüfen, Reviewkommentare bearbeiten. Sicherheitsprobleme nicht als öffentliche Bugberichte mit sensiblen Details melden; siehe [Sicherheitsrichtlinie](SECURITY.md).

Die Quellen stehen unter [AGPL-3.0-only](../LICENSE). Lizenz-/Copyright-Hinweise gemäß [REUSE](../docs/licensing.md) erhalten.
