## Context

Governance-relevant events (new external events detected, sync issues) currently have no notification channel. The `planning-slot-hybrid-sync` change introduced `ExternalEventCandidate`, and `external-event-ingestion` introduces the candidate workflow. This change adds the notification layer that tells administrators when such events occur.

The system already has Celery tasks for background work. Notifications are purely in-app (no email for MVP — email is covered by separate `configurable-email-reminders` and `event-driven-mail-hooks` changes).

## Goals / Non-Goals

**Goals:**
- Persistent `Notification` entity with type, message, read/dismiss semantics
- Automatic notification creation when `ExternalEventCandidate` is created
- API endpoint to list notifications (filtered by district, unread first)
- API endpoints to mark as read and dismiss
- Frontend notification badge with unread count
- Frontend notification center view

**Non-Goals:**
- Email delivery for notifications (separate change)
- Push notifications
- Notification preferences per user
- Notification expiry/retention policy

## Decisions

### 1. Notification Entity

```
Notification
──────────────────────
  id: UUID
  district_id: UUID (FK)
  user_id: UUID | null (null = visible to all district admins)
  notification_type: str (e.g. "EXTERNAL_EVENT_DETECTED")
  title: str
  message: str
  reference_type: str | null (e.g. "external_event_candidate")
  reference_id: UUID | null
  is_read: bool (default false)
  is_dismissed: bool (default false)
  created_at: datetime
```

**Decision:** Flexible model. `user_id` allows targeting specific users later. `reference_type` + `reference_id` allows linking to the source entity for deep linking in the UI.

### 2. Notification Scope

```
EXTERNAL_EVENT_DETECTED
  → Created by: external-event-ingestion (candidate creation)
  → Visible to: district administrators
  → Reference: ExternalEventCandidate ID (for deep-link to review modal)
```

**Decision:** Start with this single notification type. More types can be added as `event-driven-mail-hooks` is implemented.

### 3. API Design

```
GET    /api/v1/notifications?district_id={id}&unread_only=true
         → Returns notifications, newest first, with total_unread count

POST   /api/v1/notifications/{id}/read
         → Sets is_read = true

POST   /api/v1/notifications/{id}/dismiss
         → Sets is_dismissed = true

POST   /api/v1/notifications/read-all
         → Marks all unread notifications as read for the current user
```

**Decision:** Simple REST endpoints. No pagination for MVP (notifications are expected to be low volume).

### 4. Frontend Integration

```
┌─────────────────────────────────────────────┐
│  [🔔 3]  Dashboard  Matrix  Settings        │ (badge in nav)
└─────────────────────────────────────────────┘

┌── Notification Center ──────────────────────┐
│ ● Neue externe Veranstaltung erkannt         │
│   "Gottesdienst am 15.06. in Gemeinde X"     │
│   vor 5 Minuten          [Ansehen] [✕]      │
│                                             │
│ ● Neue externe Veranstaltung erkannt         │
│   "Jugendstunde am 17.06. in Gemeinde Y"     │
│   vor 2 Stunden          [Ansehen] [✕]      │
│                                             │
│                                [Alle gelesen]│
└─────────────────────────────────────────────┘
```

**Decision:** Pinia store + polling or SSE for updates. Notification badge in the top navigation bar. Click opens a slide-over or modal notification center.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| **Notification spam** — too many notifications reduce usefulness | Initially only EXTERNAL_EVENT_DETECTED. More types added deliberately. |
| **Performance** — polling API on every page load | Cache unread count locally; poll every 60s, or use SSE for real-time |
| **Stale notifications** — reference entity was deleted | Show notification but disable "view" link if reference no longer exists |