## Kontext

Der NAK District Planner hat funktionierende Backend-APIs und Vue-Frontend-Komponenten, jedoch
fehlt ein einheitliches UX-Schicht-Konzept: Es gibt weder ein globales Feedback-System noch
konsistente Leer-Zustände, Ladeanimationen oder Bestätigungsflows. Diese Lücken wurden in der
Analyse gegen OpenSpec (April 2026) als prioritär eingestuft.

## Ziele / Nicht-Ziele

**Ziele:**

- Globales Toast-/Benachrichtigungssystem für alle API-Aktionen einführen.
- Sync-Status einer Kalender-Integration im Frontend sichtbar machen.
- Alle destruktiven Aktionen hinter einem Bestätigungsdialog absichern.
- Copy-to-Clipboard für Export-Token-URLs bereitstellen.
- Leer-Zustände mit erklärendem Text und CTA in allen Listen-Views einführen.
- Matrix-Ladeanimation (Skeleton) und sticky erste Spalte implementieren.
- Gemeinde-Filter für die Matrix-Ansicht hinzufügen.

**Nicht-Ziele:**

- Vollständige mobile Alternativansicht der Matrix (separates Change-Item).
- Server-seitige Push-Benachrichtigungen (WebSocket/SSE) — nur In-App-Polling.
- E-Mail-Benachrichtigungen.

## Entscheidungen

### 1. Toast-System

**Entscheidung:** Zentraler Pinia-Store `useToastStore` mit einer Queue von Toast-Objekten
(`{ id, type: 'success'|'error'|'warning'|'info', message, timeout }`). Eine globale
`AppToast.vue`-Komponente rendert die Queue in einem fixed-positioned Container.

**Begründung:** Kein externer Dependency nötig; Tailwind-Klassen reichen für Styling aus.
Composable `useToast()` bietet einfache API: `toast.success('Gespeichert')`.

### 2. Sync-Status

**Entscheidung:** `CalendarIntegration`-Objekt bekommt `last_synced_at` (Timestamp) und
`last_sync_result` (JSONB: `{ created, updated, cancelled, errors }`). Frontend zeigt
farbcodierten Badge: Grün (≤ 2× `sync_interval`), Gelb (veraltet), Rot (Fehler).

**Begründung:** Kein neues API-Endpoint nötig; vorhandene GET-Response wird erweitert.

### 3. Bestätigungsdialoge

**Entscheidung:** Wiederverwendbares `ConfirmModal.vue` mit Props `title`, `message`,
`confirmLabel`, `dangerous` (boolean → rote Farbe). Wird per `useConfirm()`-Composable
ausgelöst.

### 4. Matrix-UX

**Entscheidung:**
- Skeleton-Screen: 5 × 4 Platzhalter-Zeilen mit Tailwind `animate-pulse bg-gray-200`.
- Sticky erste Spalte: CSS `position: sticky; left: 0` auf der ersten `<td>`.
- Scroll-Schatten: CSS box-shadow via Intersection Observer auf dem Tabellen-Container.
- Gemeinde-Filter: Clientseitiger Text-Filter auf den Matrix-Zeilen (kein API-Aufruf).

## Risiken / Trade-offs

- [Toast-Übersättigung] Zu viele gleichzeitige Toasts → Queue auf max. 3 begrenzen, älteste
  werden verdrängt.
- [Sticky-Spalte + Tailwind] Tailwind 4 unterstützt `sticky` via Utility-Klassen direkt.

## Migrationsplan

1. `useToastStore` + `AppToast.vue` implementieren; in `App.vue` einbinden.
2. Alle bestehenden API-Aufrufe in Pinia-Stores auf Toast-Feedback umstellen.
3. `CalendarIntegration`-Schema und optionale DB-Spalte erweitern.
4. `ConfirmModal.vue` + `useConfirm()` implementieren; alle destruktiven Aktionen umstellen.
5. Matrix-Skeleton, sticky Spalte, Scroll-Schatten, Gemeinde-Filter.
6. Empty-State-Komponente in allen Listen-Views einbauen.

Rollback: Toast-System ist additiv; bei Problemen einfach aus `App.vue` entfernen.
