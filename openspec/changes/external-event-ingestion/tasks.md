## 1. Domain Model

- [x] 1.1 Implement `ExternalEventCandidate` entity with status enum (PENDING, ACCEPTED, DISMISSED), content hash, and timestamps
- [x] 1.2 Separate data refresh from review-state transitions
- [x] 1.3 Add explicit candidate review exception types

## 2. Persistence Layer

- [x] 2.1 Create Alembic migration for `external_event_candidates` table
- [x] 2.2 Implement SQLAlchemy ORM model for `ExternalEventCandidateORM`
- [x] 2.3 Implement typed repository with explicit ORM/domain mapping and list/get/save methods
- [x] 2.4 Preserve provider revision and resource identifiers for reviewed mappings

## 3. Sync Integration

- [x] 3.1 Implement detection logic in sync pipeline: unmatched external event -> create candidate
- [x] 3.2 Implement deduplication check by calendar integration + external event ID
- [x] 3.3 Refresh event data, content hash, and timestamp on an existing PENDING candidate
- [x] 3.4 Implement governance-safe auto-mapping logic
- [x] 3.5 Create notification when candidate is created
- [x] 3.6 Ensure an unassignable/foreign slot does not abort the remaining sync run
- [x] 3.7 Never use event title as implicit category
- [x] 3.8 Use shared mapping logic for sync auto-match and reviewed acceptance
- [x] 3.9 Use per-event database savepoints to isolate candidate persistence failures and count failed events
- [x] 3.10 Never auto-map a terminally accepted or dismissed candidate again
- [x] 3.11 Serialize slot assignment and recheck slot occupation after acquiring an advisory lock

## 4. API Layer

- [x] 4.1 Create Pydantic schemas for ExternalEventCandidate
- [x] 4.2 Implement `GET /api/v1/external-candidates` with district/status filtering
- [x] 4.3 Implement `POST /api/v1/external-candidates/{id}/accept` with optional target PlanningSlot
- [x] 4.4 Implement `POST /api/v1/external-candidates/{id}/dismiss`
- [x] 4.5 Protect endpoints with district-admin RBAC
- [x] 4.6 Map explicit candidate review domain errors to HTTP 409
- [x] 4.7 Provide candidate repository and review service through FastAPI dependency providers
- [x] 4.8 Log candidate ingestion and review transitions with operational context

## 5. Frontend

- [ ] 5.1 Frontend review UI is intentionally out of scope for this PR and tracked in PR #390

## 6. Tests

- [x] 6.1 Unit tests for auto-mapping logic
- [x] 6.2 Unit tests for deduplication
- [x] 6.3 Unit tests for candidate API endpoints
- [x] 6.4 Candidate creation -> review flow coverage
- [x] 6.5 Regression test: foreign integration occupying an exact slot does not abort later events
- [x] 6.6 Regression tests for category-less integrations and uncategorized slots
- [x] 6.7 Tests for explicit review exceptions and terminal-state handling
- [x] 6.8 Test invalid zero/negative candidate intervals before writes
- [x] 6.9 Test missing, foreign, cancelled and already linked/dirty target slots
- [x] 6.10 Test mapping persistence failure does not mark candidate ACCEPTED
- [x] 6.11 Revalidate >=80% backend coverage on the rebased integration head (83%)
- [x] 6.12 Verify failed candidate rollback and continued processing of later provider events

## 7. Integration Prerequisites

- [x] 7.1 Reconcile with merged PR #375 sync hardening, preserving governed candidate ingestion rather than automatic slot creation
- [x] 7.2 Rebase on current `main` and reconcile the competing Alembic `0020` revisions into one linear migration chain (`0021`)
- [x] 7.3 Verify focused backend tests, OpenSpec, Alembic upgrade/head and CI on the reconciled head
