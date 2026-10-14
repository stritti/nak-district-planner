## Why

PR #376 provides the governed backend review workflow for external calendar candidates. District administrators still need a usable frontend to inspect pending candidates and decide whether to create a new planning slot, map to an existing slot, or dismiss the candidate.

## What Changes

- Add a typed frontend API client for external event candidates
- Add a Pinia store that owns candidate loading and review mutations
- Add an authenticated admin route at `/admin/external-candidates`
- Add a review view with explicit accept/create and dismiss actions
- Connect candidate-review notifications to the new route

## Dependency

This is a stacked change based on PR #376 (`vibe/external-event-candidates-7aedae`). The backend API introduced there is required.

## Scope

The first frontend slice intentionally supports accepting a candidate by creating a new PlanningSlot and dismissing it. Selecting an arbitrary existing PlanningSlot requires a dedicated searchable slot-selection UX and is kept out of this initial UI to avoid an unsafe free-form UUID input.
