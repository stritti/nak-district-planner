## Warum

Nutzer des NAK District Planners erhalten aktuell kein konsistentes Feedback zu ihren Aktionen.
Fehler werden inline ohne einheitliches Format angezeigt; Erfolgsmeldungen fehlen häufig ganz.
Destruktive Aktionen werden ohne Bestätigung ausgeführt. Die Matrix-Ansicht bietet keine
Ladeanimation und macht horizontales Scrollen nicht erkennbar. Diese Mängel beeinträchtigen die
Gebrauchstauglichkeit erheblich und können zu unbeabsichtigten Datenverlust-Aktionen führen.

## Was sich ändert

- Globales Toast/Feedback-System: Alle API-Aktionen lösen Success- oder Error-Toasts aus.
- Kalender-Integration: Sync-Status (`last_synced_at`, Ergebnis-Badge) sichtbar machen.
- Bestätigungsdialoge für destruktive Aktionen (Löschen, Ablehnen, Stornieren).
- Copy-to-Clipboard-Button neben Export-Token-URLs.
- Aussagekräftige „Empty State"-Komponenten mit CTA-Button.
- Matrix: Skeleton-Screen beim Laden, sticky erste Spalte, Scroll-Schatten, Gemeinde-Filter.

## Capabilities

### New Capabilities

- `ux-feedback`: Globales Toast-System, Sync-Status-Anzeige, Bestätigungsdialoge, Clipboard-Support
- `matrix-ux`: Skeleton-Screen, sticky Spalte, Scroll-Indikatoren, Gemeinde-Filter

### Modified Capabilities

- `service-matrix` (uc-03): Matrix-Ansicht erhält Skeleton-Screen und erweiterte Filter

## Impact

- **Frontend:** Neue Komponenten `AppToast.vue`, `ConfirmModal.vue`, `EmptyState.vue`;
  Änderungen an allen Views, die API-Aufrufe durchführen; `useToast()`-Composable + Pinia-Store
- **Backend:** `CalendarIntegration`-Schema um `last_synced_at` und `last_sync_result` erweitern
  (falls nicht schon vorhanden)
- **Datenbank:** Optional: `last_sync_result` JSONB-Spalte auf `calendar_integration`
- **Abhängigkeiten:** Keine neuen externen Abhängigkeiten
