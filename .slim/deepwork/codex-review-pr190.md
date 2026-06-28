# Codex Review PR #190 — Phase 11: Address Feedback

## Goal
Address all 27 open Codex review comments on PR #190. 15 unique items.

## Audit Status

### Already Fixed (need reply only) — 9 items
| # | Item | Fixed In | File |
|---|---|---|---|
| 1 | sync_state type before add_column | fbfbca4 | 0125 migration |
| 2 | FK constraint names | fbfbca4 | 0125 migration |
| 3 | Export: Load planning slots | a3ee057 | export.py |
| 4 | Service assignments: Resolve slot | a3ee057/d29f0b8 | service_assignments.py |
| 5 | Invitations: Resolve slot | a3ee057/d29f0b8 | invitations.py |
| 6 | tasks.py: session.commit() | 24d02f0 | tasks.py |
| 7 | sync_service: Scope links to integration | fbfbca4 | sync_service.py:143-147 |
| 8 | sync_service: Skip cancelled events | fbfbca4 | sync_service.py:155-156 |
| 9 | invitation_service: linked_event_id set | a3ee057 | invitation_service.py:141 |

### Needs Code Change — 6 items
| # | Item | Priority | File | Fix Description |
|---|---|---|---|---|
| P1a | Migration: Events before drop | P1 | 0125 migration | Add INSERT INTO event_instances FROM events |
| P1b | Export: Token scope filter | P1 | export.py | Filter all_slots by congregation_id / leader assignments |
| P1c | Notifications: District auth | P1 | notifications.py | Use CurrentUserWithMemberships, check membership |
| P1d | main.py: Events API compat | P1 | main.py + new compat router | Add events-compat router or note |
| P1e | external_event_link: save() | P1 | external_event_link.py:74 | Add `row.calendar_integration_id = link.calendar_integration_id` |
| P2f | NotificationBell: Reactivity | P2 | NotificationBell.vue:112-114 | Use storeToRefs() instead of destructuring |

## Implementation Plan

### Phase A: Quick bugfixes (3 items, can parallelize)
1. external_event_link save() — 1 line fix
2. NotificationBell.vue — storeToRefs fix
3. Notifications district auth — add membership check

### Phase B: Migration (1 item)
4. Add INSERT INTO event_instances/planning_slots BEFORE drop_table

### Phase C: Export scope + Events compat (2 items)
5. Export: Token scope filtering
6. Events compat router (or design decision)

### Phase D: Reply + Validate
7. Reply to all 27 comments with commit SHAs
8. Run tests
