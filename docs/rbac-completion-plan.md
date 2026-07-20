# RBAC Completion Plan - Task Group 1.4

> **OpenSpec Change:** introduce-rbac-permissions-model
> **Task Group:** 1.4 (Authorization Layer)
> **Priority:** 🔴 CRITICAL
> **Effort:** 16 days (3.2 weeks)
> **Status:** ✅ DONE — Siehe `docs/code-review-2026-07.md` für Verifikation
>
> **Hinweis (Juli 2026):** Dieses Dokument ist größtenteils abgeschlossen. Der `/access`-Guard in
> `auth.py` wurde implementiert, `system.py` hat Guards, die DRY-Konsolidierung auf
> `require_role_in_district()` ist abgeschlossen. Der verbleibende Punkt Task 1.4.6
> (RBAC-Coverage-Dokument) ist noch offen und wird in PR-6 des Aktionsplans adressiert.

---

## 🎯 Overview

This document provides a **detailed implementation plan** for completing RBAC (Role-Based Access Control) coverage across all API routers. Currently, **auth.py and system.py have 0 RBAC guards**, which is a critical security gap.

### Current State

| Router | RBAC Checks | Status |
|--------|-------------|--------|
| auth.py | 0 | ❌ **CRITICAL - No guards** |
| system.py | 2 | ⚠️ **Partial - /version has guard, /update has guard** |
| districts.py | 14 | ✅ Good |
| calendar_integrations.py | 6 | ✅ Good |
| events.py | 7 | ⚠️ Partial |
| export.py | 4 | ⚠️ Partial |
| invitations.py | 6 | ⚠️ Partial |
| leaders.py | 5 | ⚠️ Partial |
| registrations.py | 7 | ⚠️ Partial |
| service_assignments.py | 5 | ⚠️ Partial |

**Note:** system.py already has SOME guards (get_version requires DISTRICT_ADMIN, trigger_update requires superadmin), but needs verification.

---

## 📋 Implementation Tasks

### Task 1.4.1: Audit auth.py Router (1 day)

**Goal:** Identify all endpoints and determine required RBAC permissions.

#### Endpoints in auth.py:

| Endpoint | Method | Current Auth | Required RBAC | Notes |
|----------|--------|--------------|---------------|-------|
| `/api/v1/auth/oidc/discovery` | GET | ❌ None | **PUBLIC** | Unauthenticated - OIDC discovery |
| `/api/v1/auth/oidc/token` | POST | ❌ None | **PUBLIC** | Unauthenticated - OIDC token exchange |
| `/api/v1/auth/me` | GET | ✅ AuthenticatedUser | **VIEWER** | Requires valid token |
| `/api/v1/auth/access` | GET | ✅ RawCurrentUserWithMemberships | **VIEWER** | Returns memberships |

#### Analysis:

1. **`/oidc/discovery`** - **PUBLIC** ✅
   - Must remain unauthenticated (frontend needs it before login)
   - No RBAC guard needed

2. **`/oidc/token`** - **PUBLIC** ✅
   - Must remain unauthenticated (called during OIDC callback)
   - No RBAC guard needed

3. **`/me`** - **AUTHENTICATED** ⚠️
   - Currently requires valid Bearer token
   - Should this also require a minimum role? **Question:**
   - **Option A:** No RBAC (any authenticated user can see their own info)
   - **Option B:** Require VIEWER role (but this might break existing flows)
   - **Recommendation:** **Option A** - No RBAC, authentication is sufficient

4. **`/access`** - **AUTHENTICATED** ⚠️
   - Returns user's memberships for frontend UX
   - Should require at least VIEWER role?
   - **Recommendation:** Require VIEWER in at least one district

#### Action Items:
- [ ] Verify `/oidc/discovery` and `/oidc/token` should remain public
- [ ] Decide: Should `/me` have RBAC? (Recommendation: No)
- [ ] Decide: Should `/access` have RBAC? (Recommendation: Yes, VIEWER)
- [ ] Document decisions in this file

---

### Task 1.4.2: Add RBAC Guards to auth.py Router (3 days)

**Goal:** Implement RBAC guards based on decisions from Task 1.4.1.

#### Implementation:

```python
# services/backend/app/adapters/api/routers/auth.py

from app.adapters.api.deps import (
    AuthenticatedUser,
    RawCurrentUserWithMemberships,
    get_oidc_adapter,
)
from app.adapters.auth.permissions import (
    assert_has_role_in_district,  # NEW
    get_districts_where_user_has_role,  # NEW
)
from app.domain.models.role import Role  # NEW

# ... existing code ...

@router.get("/me", response_model=UserOut)
async def get_current_user_info(user: AuthenticatedUser) -> UserOut:
    """Get current authenticated user info.

    **Security:** Requires valid Bearer token in Authorization header.
    **RBAC:** No role requirement - any authenticated user can access their own info.
    """
    return UserOut(
        sub=user.sub,
        email=user.email,
        username=user.username,
        name=user.name,
        given_name=user.given_name,
        family_name=user.family_name,
        is_superadmin=user.is_superadmin,
    )


@router.get("/access", response_model=AccessContextOut)
async def get_access_context(auth: RawCurrentUserWithMemberships) -> AccessContextOut:
    """Return effective memberships for access-aware frontend UX.

    **Security:** Requires valid Bearer token.
    **RBAC:** Requires VIEWER role in at least one district.
    """
    # NEW: RBAC guard
    districts_with_viewer = get_districts_where_user_has_role(
        auth, Role.VIEWER
    )
    if not districts_with_viewer and not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Benutzer mit VIEWER-Rolle in mindestens einem Bezirk können auf diese Ressource zugreifen.",
        )

    memberships = [
        MembershipOut(
            role=m.role.value,
            scope_type=m.scope_type.value,
            scope_id=str(m.scope_id),
        )
        for m in auth.memberships
    ]

    status = "ACTIVE" if auth.user.is_superadmin or memberships else "PENDING_APPROVAL"
    return AccessContextOut(status=status, memberships=memberships)
```

#### Action Items:
- [ ] Add RBAC imports to auth.py
- [ ] Add RBAC guard to `/access` endpoint (if decided)
- [ ] Add comments documenting RBAC decisions
- [ ] Test all endpoints

---

### Task 1.4.3: Audit system.py Router (1 day)

**Goal:** Verify existing guards and identify missing ones.

#### Current Endpoints in system.py:

| Endpoint | Method | Current RBAC | Analysis |
|----------|--------|-------------|----------|
| `/api/v1/system/version` | GET | ✅ DISTRICT_ADMIN or CONGREGATION_ADMIN | Good - Admin only |
| `/api/v1/system/update` | POST | ✅ Superadmin only | Good - Superadmin only |

#### Analysis:

Both endpoints in system.py **already have RBAC guards**!

However, we should:
1. **Verify** the guards are correct
2. **Standardize** the guard implementation (use `assert_has_role_in_district`)
3. **Document** the RBAC requirements

#### Current Implementation:

```python
# Current in system.py - get_version
has_admin = auth.user.is_superadmin or any(
    m.role in (Role.DISTRICT_ADMIN, Role.CONGREGATION_ADMIN) for m in auth.memberships
)
if not has_admin:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Nur Administratoren können die Version abfragen.",
    )

# Current in system.py - trigger_update
if not auth.user.is_superadmin:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Nur Superadministratoren können das System aktualisieren.",
    )
```

#### Recommendation:
Use the **standardized** `assert_has_role_in_district` function for consistency.

#### Action Items:
- [ ] Verify existing guards are working correctly
- [ ] Consider standardizing to use `assert_has_role_in_district`
- [ ] Document RBAC requirements for each endpoint

---

### Task 1.4.4: Standardize RBAC Guards in system.py (2 days)

**Goal:** Use consistent RBAC guard pattern across all routers.

#### Implementation:

```python
# services/backend/app/adapters/api/routers/system.py

from app.adapters.auth.permissions import (
    assert_has_role_in_district,  # NEW
    assert_superadmin,  # NEW - or use existing pattern
)
from app.domain.models.role import Role

# ... existing code ...

@router.get("/version", response_model=SystemVersionResponse)
async def get_version(
    auth: CurrentUserWithMemberships,
    refresh: bool = Query(False, description="Force a fresh version check"),
) -> SystemVersionResponse:
    """Return the current running version and the latest available version.

    **RBAC:** Requires DISTRICT_ADMIN or CONGREGATION_ADMIN role.
    """
    # NEW: Use standardized guard
    # Note: This endpoint needs to check across ALL districts
    # For now, keep existing logic but consider refactoring
    has_admin = auth.user.is_superadmin or any(
        m.role in (Role.DISTRICT_ADMIN, Role.CONGREGATION_ADMIN) for m in auth.memberships
    )
    if not has_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Administratoren können die Version abfragen.",
        )

    # ... rest of function ...


@router.post("/update", response_model=UpdateResponse)
async def trigger_update(
    auth: CurrentUserWithMemberships,
) -> UpdateResponse:
    """Trigger a system update.

    **RBAC:** Requires superadmin role.
    """
    # NEW: Use standardized guard
    if not auth.user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur Superadministratoren können das System aktualisieren.",
        )

    # ... rest of function ...
```

#### Action Items:
- [ ] Review and potentially refactor RBAC guards in system.py
- [ ] Ensure consistency with other routers
- [ ] Add RBAC documentation comments

---

### Task 1.4.5: Audit All Other Routers (3 days)

**Goal:** Verify complete RBAC coverage across all 8 remaining routers.

#### Routers to Audit:

| Router | Current Checks | Action |
|--------|----------------|--------|
| districts.py | 14 | ✅ Verify completeness |
| calendar_integrations.py | 6 | ✅ Verify completeness |
| events.py | 7 | ⚠️ Check for missing endpoints |
| export.py | 4 | ⚠️ Check for missing endpoints |
| invitations.py | 6 | ⚠️ Check for missing endpoints |
| leaders.py | 5 | ⚠️ Check for missing endpoints |
| registrations.py | 7 | ⚠️ Check for missing endpoints |
| service_assignments.py | 5 | ⚠️ Check for missing endpoints |

#### Audit Checklist for Each Router:

1. **List all endpoints** in the router
2. **Check each endpoint** for RBAC guard
3. **Verify guard logic** is correct
4. **Document** required roles for each endpoint
5. **Identify** any endpoints without guards

#### Template for Audit Results:

```markdown
### Router: [name].py

| Endpoint | Method | RBAC Guard | Required Role | Status | Notes |
|----------|--------|------------|---------------|--------|-------|
| `/endpoint` | GET | ✅/❌ | VIEWER | ✅/❌ | - |

**Missing Guards:**
- [ ] Endpoint 1 - requires X role
- [ ] Endpoint 2 - requires Y role

**Recommendations:**
- Add guard to endpoint 1
- Verify guard logic for endpoint 2
```

#### Action Items:
- [ ] Audit districts.py
- [ ] Audit calendar_integrations.py
- [ ] Audit events.py
- [ ] Audit export.py
- [ ] Audit invitations.py
- [ ] Audit leaders.py
- [ ] Audit registrations.py
- [ ] Audit service_assignments.py
- [ ] Create audit report document

---

### Task 1.4.6: Document All Protected Endpoints (2 days)

**Goal:** Create a comprehensive RBAC coverage document.

#### Deliverable: `docs/rbac-coverage.md`

```markdown
# RBAC Coverage Report

> **Generated:** [date]
> **Status:** [Draft/Final]
> **Total Endpoints:** [X]
> **Protected Endpoints:** [Y]
> **Coverage:** [Z]%

## Summary

| Router | Total Endpoints | Protected | Coverage | Status |
|--------|-----------------|----------|----------|--------|
| auth.py | 4 | 1-2 | 25-50% | ⚠️ Partial |
| system.py | 2 | 2 | 100% | ✅ Complete |
| districts.py | 15 | 14 | 93% | ✅ Complete |
| ... | ... | ... | ... | ... |

## Detailed Coverage

### auth.py

| Endpoint | Method | Required Role | Status | Notes |
|----------|--------|---------------|--------|-------|
| `/oidc/discovery` | GET | PUBLIC | ✅ No guard needed | Unauthenticated |
| `/oidc/token` | POST | PUBLIC | ✅ No guard needed | Unauthenticated |
| `/me` | GET | AUTHENTICATED | ✅ No RBAC | Any user |
| `/access` | GET | VIEWER | ⚠️ Needs guard | Requires VIEWER in any district |

### system.py

| Endpoint | Method | Required Role | Status | Notes |
|----------|--------|---------------|--------|-------|
| `/version` | GET | DISTRICT_ADMIN or CONGREGATION_ADMIN | ✅ Guarded | - |
| `/update` | POST | SUPERADMIN | ✅ Guarded | - |

## Missing Guards

| Router | Endpoint | Method | Required Role | Priority |
|--------|----------|--------|---------------|----------|
| auth.py | `/access` | GET | VIEWER | 🟠 High |

## Recommendations

1. Add RBAC guard to auth.py `/access` endpoint
2. Standardize guard implementation across all routers
3. Add automated permission coverage test
```

#### Action Items:
- [ ] Create docs/rbac-coverage.md
- [ ] Document all endpoints with their RBAC requirements
- [ ] Identify and list all missing guards
- [ ] Add recommendations for improvement

---

### Task 1.4.7: Create Automated Permission Coverage Test (3 days)

**Goal:** Automated test to verify RBAC guard coverage.

#### Implementation: `tests/integration/test_rbac_coverage.py`

```python
"""Integration tests for RBAC permission coverage.

This test verifies that all API endpoints have appropriate RBAC guards.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.domain.models.role import Role
from app.domain.models.membership import Membership, ScopeType
import uuid


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def superadmin_token():
    """Create a JWT token for a superadmin user."""
    # Implementation depends on your JWT creation logic
    # This is a placeholder - use your actual token creation
    return "superadmin-jwt-token"


@pytest.fixture
def viewer_token(district_id):
    """Create a JWT token for a viewer user in a district."""
    return f"viewer-jwt-token-{district_id}"


@pytest.fixture
def planner_token(district_id):
    """Create a JWT token for a planner user in a district."""
    return f"planner-jwt-token-{district_id}"


@pytest.fixture
def unauthenticated_client(client):
    """Client with no authentication."""
    return client


@pytest.fixture
def district_id():
    """Sample district ID."""
    return uuid.uuid4()


class TestRBACCoverage:
    """Test RBAC guard coverage across all endpoints."""

    # Public endpoints (should work without auth)
    PUBLIC_ENDPOINTS = [
        ("/api/v1/auth/oidc/discovery", "GET"),
        ("/api/v1/auth/oidc/token", "POST"),
        ("/api/health", "GET"),
    ]

    # Endpoints that should require authentication
    AUTHENTICATED_ENDPOINTS = [
        ("/api/v1/auth/me", "GET"),
        ("/api/v1/auth/access", "GET"),
    ]

    # Endpoints that should require specific roles
    ROLE_REQUIRED_ENDPOINTS = {
        "VIEWER": [
            ("/api/v1/districts", "GET"),
            ("/api/v1/districts/{district_id}/matrix", "GET"),
            # Add more viewer endpoints
        ],
        "PLANNER": [
            ("/api/v1/events", "POST"),
            ("/api/v1/service_assignments", "POST"),
            # Add more planner endpoints
        ],
        "DISTRICT_ADMIN": [
            ("/api/v1/system/version", "GET"),
            ("/api/v1/leaders", "POST"),
            # Add more admin endpoints
        ],
        "SUPERADMIN": [
            ("/api/v1/system/update", "POST"),
            ("/api/v1/districts", "POST"),
            # Add more superadmin endpoints
        ],
    }

    @pytest.mark.parametrize("endpoint,method", PUBLIC_ENDPOINTS)
    def test_public_endpoints_accessible_without_auth(
        self, unauthenticated_client, endpoint, method
    ):
        """Public endpoints should be accessible without authentication."""
        # Format endpoint with sample IDs if needed
        test_endpoint = endpoint.format(district_id=uuid.uuid4())

        if method == "GET":
            response = unauthenticated_client.get(test_endpoint)
        elif method == "POST":
            response = unauthenticated_client.post(test_endpoint, json={})
        else:
            pytest.skip(f"Method {method} not implemented in test")

        # Public endpoints should return 200 or 400 (bad request), not 401/403
        assert response.status_code not in [401, 403], (
            f"Public endpoint {endpoint} returned {response.status_code}"
        )

    @pytest.mark.parametrize("endpoint,method", AUTHENTICATED_ENDPOINTS)
    def test_authenticated_endpoints_require_auth(
        self, unauthenticated_client, endpoint, method
    ):
        """Authenticated endpoints should require valid authentication."""
        test_endpoint = endpoint.format(district_id=uuid.uuid4())

        if method == "GET":
            response = unauthenticated_client.get(test_endpoint)
        elif method == "POST":
            response = unauthenticated_client.post(test_endpoint, json={})
        else:
            pytest.skip(f"Method {method} not implemented in test")

        # Should return 401 (unauthorized) without valid token
        assert response.status_code == 401, (
            f"Authenticated endpoint {endpoint} should require auth, got {response.status_code}"
        )

    @pytest.mark.parametrize("role,endpoints", ROLE_REQUIRED_ENDPOINTS.items())
    @pytest.mark.parametrize("endpoint,method", endpoints)
    def test_role_required_endpoints(
        self, client, role, endpoint, method, district_id
    ):
        """Endpoints requiring specific roles should enforce RBAC."""
        test_endpoint = endpoint.format(district_id=district_id)

        # Test with viewer token (should fail for PLANNER/DISTRICT_ADMIN/SUPERADMIN endpoints)
        if role != "VIEWER":
            client.headers["Authorization"] = f"Bearer {viewer_token(district_id)}"
            if method == "GET":
                response = client.get(test_endpoint)
            else:
                response = client.post(test_endpoint, json={})

            # Should return 403 for insufficient permissions
            assert response.status_code == 403, (
                f"Endpoint {endpoint} requiring {role} should reject VIEWER, got {response.status_code}"
            )

        # Test with correct role token (should succeed)
        if role == "VIEWER":
            client.headers["Authorization"] = f"Bearer {viewer_token(district_id)}"
        elif role == "PLANNER":
            client.headers["Authorization"] = f"Bearer {planner_token(district_id)}"
        elif role == "DISTRICT_ADMIN":
            client.headers["Authorization"] = f"Bearer {district_admin_token(district_id)}"
        elif role == "SUPERADMIN":
            client.headers["Authorization"] = f"Bearer {superadmin_token()}"

        if method == "GET":
            response = client.get(test_endpoint)
        else:
            response = client.post(test_endpoint, json={})

        # Should succeed with correct role
        assert response.status_code not in [401, 403], (
            f"Endpoint {endpoint} requiring {role} should accept {role} token, got {response.status_code}"
        )


class TestRBACGuardConsistency:
    """Test that RBAC guards are implemented consistently."""

    def test_all_guards_use_permissions_module(self, client):
        """All RBAC guards should use the permissions module."""
        # This is a static analysis test - would need to inspect source code
        # For now, this is a placeholder for manual verification
        pass

    def test_all_guards_check_memberships(self, client):
        """All RBAC guards should check user memberships."""
        # Placeholder for static analysis
        pass
```

#### Action Items:
- [ ] Create test file `tests/integration/test_rbac_coverage.py`
- [ ] Implement public endpoint tests
- [ ] Implement authenticated endpoint tests
- [ ] Implement role-required endpoint tests
- [ ] Add test for guard consistency
- [ ] Ensure tests run in CI

---

## 📊 Timeline

| Task | Duration | Start | End | Assignee |
|------|----------|-------|-----|----------|
| 1.4.1: Audit auth.py | 1 day | Day 1 | Day 1 | - |
| 1.4.2: Add RBAC to auth.py | 3 days | Day 2 | Day 4 | - |
| 1.4.3: Audit system.py | 1 day | Day 5 | Day 5 | - |
| 1.4.4: Standardize system.py | 2 days | Day 6 | Day 7 | - |
| 1.4.5: Audit all routers | 3 days | Day 8 | Day 10 | - |
| 1.4.6: Document coverage | 2 days | Day 11 | Day 12 | - |
| 1.4.7: Create coverage test | 3 days | Day 13 | Day 15 | - |

**Total:** 15 days (3 weeks)

---

## 🎯 Acceptance Criteria

- [ ] All endpoints in auth.py have appropriate RBAC guards
- [ ] All endpoints in system.py use standardized RBAC guard pattern
- [ ] All endpoints in other routers have been audited
- [ ] RBAC coverage document is complete
- [ ] Automated permission coverage test exists and passes
- [ ] All existing functionality remains intact
- [ ] No security regressions introduced

---

## 📚 Related Documents

- [OpenSpec RBAC Change](/openspec/changes/introduce-rbac-permissions-model/)
- [RBAC Model Spec](/openspec/changes/introduce-rbac-permissions-model/specs/rbac-model/spec.md)
- [Implementation Tasks](/docs/implementation-tasks.md)
- [Gap Analysis](/docs/openspec-gap-analysis.md)

---

## 🔗 Quick Links

- [auth.py router](/services/backend/app/adapters/api/routers/auth.py)
- [system.py router](/services/backend/app/adapters/api/routers/system.py)
- [permissions module](/services/backend/app/adapters/auth/permissions.py)
- [role model](/services/backend/app/domain/models/role.py)

---

*Generated by Mistral Vibe Code - RBAC Completion Plan*
