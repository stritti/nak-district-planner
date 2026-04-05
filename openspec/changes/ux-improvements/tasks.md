## 1. Toast System

- [ ] 1.1 Create `useToastStore` Pinia store (queue, add, remove actions)
- [ ] 1.2 Create `AppToast.vue` component (fixed-position container, auto-dismiss)
- [ ] 1.3 Register `AppToast.vue` in `App.vue`
- [ ] 1.4 Create `useToast()` composable wrapping the store
- [ ] 1.5 Update all Pinia store API calls to emit success/error toasts

## 2. Sync Status

- [ ] 2.1 Add `last_synced_at` and `last_sync_result` fields to `CalendarIntegration` domain model
- [ ] 2.2 Update sync service to write `last_synced_at` and `last_sync_result` after each sync run
- [ ] 2.3 Create Alembic migration for `last_sync_result` JSONB column on `calendar_integration`
- [ ] 2.4 Update `CalendarIntegrationResponse` schema to include both new fields
- [ ] 2.5 Display color-coded sync status badge in `CalendarIntegrationsView.vue`
- [ ] 2.6 Add tooltip showing created/updated/cancelled counts on hover

## 3. Confirmation Dialogs

- [ ] 3.1 Create `ConfirmModal.vue` (title, message, confirmLabel, dangerous props)
- [ ] 3.2 Create `useConfirm()` composable (returns a Promise resolved on confirm/cancel)
- [ ] 3.3 Wrap all delete actions in `CalendarIntegrationsView.vue` with `useConfirm()`
- [ ] 3.4 Wrap all delete/reject actions in registration management with `useConfirm()`
- [ ] 3.5 Wrap event cancel/delete actions with `useConfirm()`

## 4. Copy to Clipboard

- [ ] 4.1 Create reusable `CopyButton.vue` component (Clipboard API + "Kopiert!" feedback)
- [ ] 4.2 Use `CopyButton.vue` in export token display views

## 5. Empty States

- [ ] 5.1 Create `EmptyState.vue` component (icon, message, optional CTA button)
- [ ] 5.2 Add empty state to `EventListView.vue`
- [ ] 5.3 Add empty state to `CalendarIntegrationsView.vue`
- [ ] 5.4 Add empty state to leader management views

## 6. Matrix UX Enhancements

- [ ] 6.1 Add skeleton loading screen to `MatrixView.vue` (animate-pulse placeholder rows)
- [ ] 6.2 Make first column sticky (`position: sticky; left: 0`) in matrix table
- [ ] 6.3 Add scroll-shadow CSS via Intersection Observer on the matrix table container
- [ ] 6.4 Add congregation text filter input to matrix filter bar (client-side filtering)
