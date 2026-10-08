## Why

Die Workflows referenzieren Actions über verschiebbare Tags (`@v7`). Ein kompromittiertes oder neu gesetztes Tag einer Drittanbieter-Action liefe sofort mit dem `GITHUB_TOKEN` und den Release-Secrets (GHCR-Push, release-please). Außerdem hatte der gesamte CI-Workflow `pull-requests: write`, obwohl nur der Coverage-Kommentar Schreibrechte braucht (#473).

## What Changes

- Jede `uses:`-Referenz in `.github/workflows/` ist auf einen vollständigen Commit-SHA gepinnt, mit der Release-Version als Kommentar. Dependabot (`github-actions`) aktualisiert SHA und Kommentar.
- `ci.yml` vergibt auf Workflow-Ebene nur `contents: read`; `pull-requests: write` hat ausschließlich der Backend-Job, der den Coverage-Kommentar schreibt.

## Impact

- Betroffen: alle Workflows unter `.github/workflows/`.
- Kein Einfluss auf Anwendungscode oder Laufzeit.
