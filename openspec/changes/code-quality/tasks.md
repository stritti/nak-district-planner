## 1. Backend: Sync Service Refactoring

- [ ] 1.1 Replace `_get_connector()` `if/elif` chain with `_CONNECTOR_MAP` dictionary registry
- [ ] 1.2 Add `NotImplementedError` to `GoogleCalendarConnector` and `MicrosoftGraphCalendarConnector` stubs
- [ ] 1.3 Add Celery async bridge comment in `tasks.py` (explains `asyncio.run()` usage)

## 2. Backend: Typed Result Objects

- [ ] 2.1 Create `SyncResult` dataclass in `application/sync/results.py`
- [ ] 2.2 Update `sync_service.py` to return `SyncResult` instead of `dict[str, int]`
- [ ] 2.3 Update Celery task and API response to use `SyncResult`

## 3. Backend: Dependency Injection Patterns

- [ ] 3.1 Audit all FastAPI routers for inconsistent session/service injection
- [ ] 3.2 Standardize all routers to use `Depends(get_<service>)` pattern
- [ ] 3.3 Add type annotations to all `Depends()` parameters

## 4. Backend: Health Check Endpoint

- [ ] 4.1 Implement `GET /health` endpoint in a dedicated router
- [ ] 4.2 Add DB ping (SQLAlchemy `text("SELECT 1")`) and Redis ping checks
- [ ] 4.3 Return HTTP 200 when healthy, HTTP 503 when degraded
- [ ] 4.4 Register `/health` router in `main.py`
- [ ] 4.5 Update `docker-compose.yml` `backend` service to use `GET /health` as healthcheck

## 5. Frontend: HTTP Client

- [ ] 5.1 Create `src/services/api/httpClient.ts` (axios instance or fetch wrapper)
- [ ] 5.2 Add auth token injection interceptor
- [ ] 5.3 Add global 401 handler (trigger logout)
- [ ] 5.4 Migrate all existing API files to use `httpClient` instead of raw `fetch`/`axios`

## 6. Frontend: OAuth Stub UI

- [ ] 6.1 Add "Coming soon" badge in integration form for Google and Microsoft types
- [ ] 6.2 Disable integration form submit button when Google/Microsoft type is selected

## 7. Frontend: View Component Decomposition

- [ ] 7.1 Extract `EventFilters.vue` from `EventListView.vue`
- [ ] 7.2 Extract `EventTable.vue` from `EventListView.vue`
- [ ] 7.3 Extract `EventFormModal.vue` from `EventListView.vue`
- [ ] 7.4 Extract `IntegrationCard.vue` from `CalendarIntegrationsView.vue`
- [ ] 7.5 Extract `IntegrationFormModal.vue` from `CalendarIntegrationsView.vue`
- [ ] 7.6 Extract `MatrixFilters.vue` from `MatrixView.vue`
- [ ] 7.7 Extract `MatrixTable.vue` from `MatrixView.vue`
