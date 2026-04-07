# Congregation Grouping Rollout

## Scope

This change introduces optional grouping metadata for congregations and consumes it in district overview and matrix sorting.

## Deployment Notes

- Ensure the existing migration adding `congregation_groups` and `congregations.group_id` is applied in all environments before deploying frontend changes that rely on grouped rendering.
- Backend remains backward-compatible: requests without `group_id` continue to work and response fields may return `null` for group metadata.
- Frontend defaults to existing matrix order; grouped sorting is opt-in (`Sortierung: Nach Gruppen`).

## Fallback Behavior

- Congregations without group assignment are shown in an explicit ungrouped section in district overview.
- If group metadata is unavailable for a congregation, UI falls back to existing flat behavior and does not block editing.
- If matrix grouped sorting is disabled, row ordering follows previous behavior.
