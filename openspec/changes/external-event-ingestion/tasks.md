## 1. Domain Model

- [ ] 1.1 Implement `ExternalEventCandidate` entity with status enum (PENDING, ACCEPTED, DISMISSED)

## 2. Persistence Layer

- [ ] 2.1 Create Alembic migration for `external_event_candidates` table
- [ ] 2.2 Implement SQLAlchemy ORM model for `ExternalEventCandidateORM`
- [ ] 2.3 Implement repository with list (filterable by district/status), create, update methods

## 3. Sync Integration

- [ ] 3.1 Implement detection logic in sync pipeline: unmatched external event → create candidate
- [ ] 3.2 Implement deduplication check (by external_event_id + source)
- [ ] 3.3 Implement auto-mapping logic (exact match on congregation, date, time, category)
- [ ] 3.4 Create notification when candidate is created (integrate with in-app-notifications)

## 4. API Layer

- [ ] 4.1 Create Pydantic schemas for ExternalEventCandidate
- [ ] 4.2 Implement `GET /api/v1/external-candidates` (filterable by district, status)
- [ ] 4.3 Implement `POST /api/v1/external-candidates/{id}/accept` (with optional target PlanningSlot)
- [ ] 4.4 Implement `POST /api/v1/external-candidates/{id}/dismiss`
- [ ] 4.5 Protect endpoints with RBAC (district admin)

## 5. Frontend

- [ ] 5.1 Add API client methods for candidate CRUD
- [ ] 5.2 Add Pinia store for candidates
- [ ] 5.3 Implement candidate review list view (pending candidates)
- [ ] 5.4 Implement candidate review modal (accept with/without mapping, dismiss)

## 6. Tests

- [ ] 6.1 Unit tests for auto-mapping logic
- [ ] 6.2 Unit tests for deduplication
- [ ] 6.3 Unit tests for candidate API endpoints
- [ ] 6.4 Integration tests for full candidate creation → review flow
