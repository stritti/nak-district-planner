## 1. Congregation dialog
- [x] 1.1 Revision, row lock and `If-Match` on `PATCH /districts/{id}/congregations/{id}`; unit tests for 428/412/permission order
- [x] 1.2 Frontend sends the opened revision, handles 412/428 by refreshing the list

## 2. Reminder configurations and event hooks
- [x] 2.1 Revision and `If-Match` on `PUT`/`DELETE /reminder-configs/{id}` (dialog and active switch; DELETE returns the updated record)
- [x] 2.2 Revision and `If-Match` on `PUT /event-hooks/{id}` (dialog and active switch)
- [x] 2.3 Frontend clients and views send the revision and handle stale writes

## 3. Organisational duties panel
- [ ] 3.1 Revision and `If-Match` on duty assignment and suggestion changes
- [ ] 3.2 Frontend panel sends the revision and handles stale writes

## 4. Closure
- [ ] 4.1 Baseline spec updated, change archived
