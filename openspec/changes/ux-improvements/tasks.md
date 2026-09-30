## 1. Toast System

- [x] 1.1 Create `useToastStore` Pinia store (queue, add, remove actions) *(`src/stores/toast.ts`)*
- [x] 1.2 Create `AppToast.vue` component (fixed-position container, auto-dismiss) *(als `ToastContainer.vue` umgesetzt)*
- [x] 1.3 Register `AppToast.vue` in `App.vue` *(`ToastContainer` ist registriert)*
- [x] 1.4 Create `useToast()` composable wrapping the store *(`composables/useToast.ts` inkl. `errorMessage()` zur einheitlichen Fehlernormalisierung)*
- [ ] 1.5 Update all Pinia store API calls to emit success/error toasts *(Events: Bearbeiten-Dialog nutzt `useToast()`; Matrix/Invitations weiterhin offen)*

## 2. Sync Status

- [x] 2.1 Add `last_synced_at` and `last_sync_result` fields to `CalendarIntegration` domain model *(`last_synced_at` + `last_sync_error` statt JSONB `last_sync_result`)*
- [x] 2.2 Update sync service to write `last_synced_at` and `last_sync_result` after each sync run *(schreibt `last_synced_at` + `last_sync_error`)*
- [x] 2.3 Create Alembic migration for `last_sync_result` JSONB column on `calendar_integration` *(`0013_calendar_integration_last_sync_error.py` — String-Spalte statt JSONB)*
- [x] 2.4 Update `CalendarIntegrationResponse` schema to include both new fields
- [x] 2.5 Display color-coded sync status badge in `CalendarIntegrationsView.vue` *(`SyncStatusCard.vue` mit Status-Punkt + Typ-Badge)*
- [x] 2.6 Add tooltip showing created/updated/cancelled counts on hover *(`SyncStatusCard.vue` zeigt created/updated/cancelled/auto_matched)*

## 3. Confirmation Dialogs

- [x] 3.1 Create `ConfirmModal.vue` (title, message, confirmLabel, dangerous props) *(als `ConfirmDialog.vue` umgesetzt)*
- [x] 3.2 Create `useConfirm()` composable (returns a Promise resolved on confirm/cancel) *(auf `useConfirmDialog` aus `@vueuse/core`; ein globaler `ConfirmHost` in `App.vue`)*
- [x] 3.3 Wrap all delete actions in `CalendarIntegrationsView.vue` with `useConfirm()` *(via `ConfirmDialog`)*
- [x] 3.4 Wrap all delete/reject actions in registration management with `useConfirm()` *(geprüft: Löschen nutzt bereits `ConfirmDialog` mit Ladezustand, Ablehnen ein Begründungs-Modal — keine ungesicherte Aktion; Umstellung auf `useConfirm()` bringt keinen Mehrwert)*
- [x] 3.5 Wrap event cancel/delete actions with `useConfirm()` *(Absagen im Bearbeiten-Dialog; ein Lösch-Endpunkt für Events existiert nicht)*

## 4. Copy to Clipboard

- [x] 4.1 Create reusable `CopyButton.vue` component (Clipboard API + "Kopiert!" feedback) *(`useClipboard` aus `@vueuse/core` mit Legacy-Fallback; zeigt Fehler statt unbehandelter Promise-Rejection)*
- [x] 4.2 Use `CopyButton.vue` in export token display views *(ExportTokensView, Leader-Export-Dialog)*

## 5. Empty States

- [x] 5.1 Create `EmptyState.vue` component (icon, message, optional CTA button)
- [x] 5.2 Add empty state to `EventListView.vue`
- [x] 5.3 Add empty state to `CalendarIntegrationsView.vue` *(mit CTA „Integration anlegen“)*
- [x] 5.4 Add empty state to leader management views

## 6. Matrix UX Enhancements

- [ ] 6.1 Add skeleton loading screen to `MatrixView.vue` (animate-pulse placeholder rows)
- [x] 6.2 Make first column sticky (`position: sticky; left: 0`) in matrix table *(`MatrixTable.vue`)*
- [ ] 6.3 Add scroll-shadow CSS via Intersection Observer on the matrix table container
- [ ] 6.4 Add congregation text filter input to matrix filter bar (client-side filtering)
