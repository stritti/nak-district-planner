## Context

Der NAK District Planner ist eine Multi-Tenant Anwendung mit:
- **Districts** (Bezirke) als Root-Tenants
- **Congregations** (Gemeinden) als Sub-Tenants
- **Users** mit Memberships in bestimmten Tenants
- **Events, ServiceAssignments, CalendarIntegrations** als Tenant-spezifische Daten

Aktuell gibt es Tenant-Isolation auf Application-Ebene (Membership-Gate), aber keine Datenbank-Ebene Isolation.

## Goals / Non-Goals

**Goals:**
- Vollständige Tenant-Isolation auf Application- und Datenbank-Ebene
- Verhindern von Cross-Tenant Data Access
- Defense in Depth durch mehrere Isolation-Schichten
- Minimaler Performance-Impact (< 2%)
- Kompatibilität mit bestehendem Rollenmodell

**Non-Goals:**
- Isolation auf Netzwerkebene (ist Aufgabe der Infrastruktur)
- Isolation auf Dateisystem-Ebene (nicht relevant)
- Kryptografische Isolation (nicht nötig)

## Decisions

### 1. Multi-Layer Tenant-Isolation

**Architektur:**

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ Tenant Middleware│    │ Tenant Context  │    │ Permission  │ │
│  │ (Request Level) │    │ (ContextVar)     │    │ Checks      │ │
│  └────────┬────────┘    └────────┬────────┘    └──────┬──────┘ │
│           │                      │                     │         │
│           └──────────────────────┼─────────────────────┘         │
│                                  │                                   │
│                                  ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      Service Layer                              │ │
│  │  ┌─────────────────────────────────────────────────────────┐│ │
│  │  │ - TenantValidationService                                ││ │
│  │  │ - TenantAwareRepository (Base Class)                      ││ │
│  │  └─────────────────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                  │                                   │
│                                  ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      Data Layer                                │ │
│  │  ┌─────────────────────────────────────────────────────────┐│ │
│  │  │ - PostgreSQL RLS Policies                                ││ │
│  │  │ - Tenant-specific Queries                                 ││ │
│  │  └─────────────────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Tenant Context

**Kontextvariable für aktuellen Tenant:**

```python
# app/tenant.py
from contextvars import ContextVar
from typing import Optional
import uuid

# Kontextvariable für aktuellen Tenant
current_tenant: ContextVar[Optional[uuid.UUID]] = ContextVar("current_tenant", default=None)
current_district: ContextVar[Optional[uuid.UUID]] = ContextVar("current_district", default=None)
current_user_sub: ContextVar[Optional[str]] = ContextVar("current_user_sub", default=None)

class TenantContext:
    """Hilfsklasse für Tenant-Kontext."""
    
    @staticmethod
    def get_tenant() -> uuid.UUID | None:
        """Hole aktuellen Tenant."""
        return current_tenant.get()
    
    @staticmethod
    def get_district() -> uuid.UUID | None:
        """Hole aktuellen Bezirk."""
        return current_district.get()
    
    @staticmethod
    def get_user_sub() -> str | None:
        """Hole aktuellen User Sub."""
        return current_user_sub.get()
    
    @staticmethod
    def set_context(
        tenant_id: uuid.UUID | None = None,
        district_id: uuid.UUID | None = None,
        user_sub: str | None = None,
    ):
        """Setze Tenant-Kontext."""
        token = current_tenant.set(tenant_id)
        current_district.set(district_id)
        current_user_sub.set(user_sub)
        return token
    
    @staticmethod
    def reset(token):
        """Setze Kontext zurück."""
        current_tenant.reset(token)
        current_district.reset()
        current_user_sub.reset()
```

### 3. Tenant Middleware

**Extraktion des Tenant-Kontexts aus Requests:**

```python
# app/adapters/api/middleware/tenant.py
from fastapi import Request
from typing import Callable, Awaitable
from app.tenant import TenantContext
from app.adapters.auth.permissions import has_role_in_district
from app.domain.models.role import Role
import uuid

class TenantMiddleware:
    """FastAPI Middleware für Tenant-Kontext."""
    
    def __init__(
        self,
        app,
        exempt_paths: set[str] | None = None,
        exempt_methods: set[str] | None = None,
    ):
        self.app = app
        self.exempt_paths = exempt_paths or {"/api/health", "/api/v1/auth/oidc/discovery"}
        self.exempt_methods = exempt_methods or {"GET", "HEAD", "OPTIONS"}
        
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Skip für exempt paths/methods
        if request.url.path in self.exempt_paths or request.method in self.exempt_methods:
            return await call_next(request)
        
        # Extrahiere Tenant-Informationen
        tenant_id = None
        district_id = None
        user_sub = None
        
        # Von JWT Token
        if hasattr(request.state, "user"):
            user = request.state.user
            user_sub = getattr(user, "sub", None)
            
            # Für Superadmin: Kein Tenant-Limit
            if getattr(user, "is_superadmin", False):
                tenant_id = None  # Superadmin sieht alle Tenants
                district_id = None
            else:
                # Extrahiere District aus Memberships
                if hasattr(user, "memberships"):
                    for membership in user.memberships:
                        if membership.scope_type == "DISTRICT":
                            district_id = membership.scope_id
                            tenant_id = district_id
                            break
        
        # Von API Key
        if not tenant_id and hasattr(request.state, "api_key"):
            api_key = request.state.api_key
            tenant_id = getattr(api_key, "district_id", None)
            district_id = tenant_id
        
        # Setze Kontext
        token = TenantContext.set_context(
            tenant_id=tenant_id,
            district_id=district_id,
            user_sub=user_sub,
        )
        
        try:
            response = await call_next(request)
            return response
        finally:
            TenantContext.reset(token)
```

### 4. PostgreSQL Row-Level Security (RLS)

**RLS Policies für Tenant-Isolation:**

```sql
-- RLS für alle Tenant-spezifischen Tabellen aktivieren

-- Events Tabelle
ALTER TABLE events ENABLE ROW LEVEL SECURITY;

-- Policy: Nutzer können nur Events im eigenen Bezirk sehen
CREATE POLICY tenant_isolation_events ON events
    FOR ALL
    USING (
        -- Superadmin sieht alles
        (current_setting('app.current_user_is_superadmin') = 'true') OR
        -- District Admin sieht Events im eigenen Bezirk
        (district_id = current_setting('app.current_district_id')::uuid) OR
        -- Congregation Admin sieht Events in eigenen Gemeinden
        (congregation_id IN (
            SELECT scope_id FROM memberships 
            WHERE user_sub = current_setting('app.current_user_sub') 
            AND scope_type = 'CONGREGATION'
        ))
    );

-- ServiceAssignments Tabelle
ALTER TABLE service_assignments ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_service_assignments ON service_assignments
    FOR ALL
    USING (
        (current_setting('app.current_user_is_superadmin') = 'true') OR
        (event_id IN (
            SELECT id FROM events
            WHERE district_id = current_setting('app.current_district_id')::uuid
        ))
    );

-- CalendarIntegrations Tabelle
ALTER TABLE calendar_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_calendar_integrations ON calendar_integrations
    FOR ALL
    USING (
        (current_setting('app.current_user_is_superadmin') = 'true') OR
        (district_id = current_setting('app.current_district_id')::uuid)
    );

-- Districts Tabelle (nur für Superadmin)
ALTER TABLE districts ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_districts ON districts
    FOR SELECT
    USING (
        (current_setting('app.current_user_is_superadmin') = 'true') OR
        (id = current_setting('app.current_district_id')::uuid)
    );

CREATE POLICY tenant_isolation_districts_insert ON districts
    FOR INSERT
    WITH CHECK (
        current_setting('app.current_user_is_superadmin') = 'true'
    );

-- Congregations Tabelle
ALTER TABLE congregations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_congregations ON congregations
    FOR ALL
    USING (
        (current_setting('app.current_user_is_superadmin') = 'true') OR
        (district_id = current_setting('app.current_district_id')::uuid)
    );
```

**Middleware zur Setzung von PostgreSQL Settings:**

```python
# app/adapters/db/session.py
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.tenant import TenantContext

@event.listens_for(Engine, "before_cursor_execute")
def set_tenant_context(conn, cursor, statement, parameters, context, executemany):
    """Setze Tenant-Kontext für PostgreSQL RLS."""
    tenant_id = TenantContext.get_tenant()
    district_id = TenantContext.get_district()
    user_sub = TenantContext.get_user_sub()
    is_superadmin = "false"
    
    # Prüfe ob Superadmin
    if user_sub:
        # Hier müsste die Superadmin-Prüfung implementiert werden
        # Für jetzt: Annahme dass Superadmin in user_sub markiert ist
        if user_sub.startswith("superadmin:"):
            is_superadmin = "true"
    
    # Setze PostgreSQL Settings
    if tenant_id:
        conn.execute(f"SET app.current_tenant_id = '{tenant_id}'")
    else:
        conn.execute("SET app.current_tenant_id = NULL")
    
    if district_id:
        conn.execute(f"SET app.current_district_id = '{district_id}'")
    else:
        conn.execute("SET app.current_district_id = NULL")
    
    if user_sub:
        conn.execute(f"SET app.current_user_sub = '{user_sub}'")
    else:
        conn.execute("SET app.current_user_sub = NULL")
    
    conn.execute(f"SET app.current_user_is_superadmin = {is_superadmin}")
```

### 5. Tenant-Aware Repositories

**Basis-Klasse für Tenant-aware Repositories:**

```python
# app/adapters/db/repositories/base.py
from typing import Optional, TypeVar, Generic
import uuid
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.tenant import TenantContext
from app.domain.models.membership import ScopeType

T = TypeVar('T')

class TenantAwareRepository(Generic[T]):
    """Basis-Klasse für Tenant-aware Repositories."""
    
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class
        
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        district_id: Optional[uuid.UUID] = None,
        congregation_id: Optional[uuid.UUID] = None,
        **filters,
    ) -> tuple[list[T], int]:
        """Liste Entitäten mit Tenant-Filter."""
        # Hole Tenant-Kontext
        current_district = TenantContext.get_district()
        current_user_sub = TenantContext.get_user_sub()
        is_superadmin = self._is_superadmin()
        
        # Baue Query
        stmt = select(self.model_class)
        
        # Tenant-Filter
        if not is_superadmin:
            # Filter nach District
            if district_id:
                stmt = stmt.where(self.model_class.district_id == district_id)
            elif current_district:
                stmt = stmt.where(self.model_class.district_id == current_district)
            
            # Filter nach Congregation
            if congregation_id:
                stmt = stmt.where(self.model_class.congregation_id == congregation_id)
        
        # Weitere Filter
        for field, value in filters.items():
            if hasattr(self.model_class, field):
                stmt = stmt.where(getattr(self.model_class, field) == value)
        
        # Limit und Offset
        stmt = stmt.limit(limit).offset(offset)
        
        # Führe Query aus
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        
        # Zähle Gesamtzahl
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar()
        
        return items, total
    
    async def get(self, id: uuid.UUID) -> Optional[T]:
        """Hole Entität mit Tenant-Filter."""
        current_district = TenantContext.get_district()
        is_superadmin = self._is_superadmin()
        
        stmt = select(self.model_class).where(self.model_class.id == id)
        
        # Tenant-Filter
        if not is_superadmin and current_district:
            stmt = stmt.where(self.model_class.district_id == current_district)
        
        result = await self.session.execute(stmt)
        return result.scalar()
    
    async def save(self, entity: T) -> T:
        """Speichere Entität mit Tenant-Validierung."""
        current_district = TenantContext.get_district()
        is_superadmin = self._is_superadmin()
        
        # Validierung
        if not is_superadmin:
            if hasattr(entity, 'district_id') and entity.district_id != current_district:
                raise PermissionError("Cannot save entity in different district")
        
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, id: uuid.UUID) -> bool:
        """Lösche Entität mit Tenant-Validierung."""
        entity = await self.get(id)
        if not entity:
            return False
        
        current_district = TenantContext.get_district()
        is_superadmin = self._is_superadmin()
        
        # Validierung
        if not is_superadmin:
            if hasattr(entity, 'district_id') and entity.district_id != current_district:
                raise PermissionError("Cannot delete entity in different district")
        
        await self.session.delete(entity)
        await self.session.commit()
        return True
    
    def _is_superadmin(self) -> bool:
        """Prüfe ob aktueller Nutzer Superadmin ist."""
        user_sub = TenantContext.get_user_sub()
        if user_sub:
            # Hier müsste die Superadmin-Prüfung implementiert werden
            return user_sub.startswith("superadmin:")
        return False
```

### 6. Tenant Validation Service

**Service zur expliziten Tenant-Validierung:**

```python
# app/application/tenant_validation.py
from typing import Optional
import uuid
from app.tenant import TenantContext
from app.adapters.auth.permissions import has_role_in_district, has_role_in_congregation
from app.domain.models.role import Role

class TenantValidationError(Exception):
    """Raised when tenant validation fails."""
    pass

class TenantValidationService:
    """Service für Tenant-Validierung."""
    
    def __init__(self, audit_service: Optional[any] = None):
        self.audit_service = audit_service
        
    def validate_district_access(
        self,
        district_id: uuid.UUID,
        required_role: Role | None = None,
    ) -> bool:
        """
        Validiere Zugriff auf einen Bezirk.
        
        Args:
            district_id: ID des Bezirks
            required_role: Erforderliche Rolle (optional)
            
        Returns:
            True wenn Zugriff erlaubt
            
        Raises:
            TenantValidationError: Wenn Zugriff verweigert
        """
        current_district = TenantContext.get_district()
        current_user_sub = TenantContext.get_user_sub()
        is_superadmin = self._is_superadmin()
        
        # Superadmin hat Zugriff auf alle Bezirke
        if is_superadmin:
            return True
        
        # Prüfe ob Nutzer Zugriff auf den Bezirk hat
        if current_district != district_id:
            if self.audit_service:
                import asyncio
                asyncio.create_task(
                    self.audit_service.log_action(
                        action="ACCESS_DENIED",
                        resource_type="District",
                        resource_id=district_id,
                        user_sub=current_user_sub,
                        error_message="Cross-tenant access attempt",
                        status="failed",
                    )
                )
            raise TenantValidationError(
                f"User {current_user_sub} cannot access district {district_id}"
            )
        
        # Prüfe Rolle
        if required_role:
            from app.adapters.auth.permissions import has_role_in_district
            if not has_role_in_district(current_user_sub, required_role, district_id):
                raise TenantValidationError(
                    f"User {current_user_sub} lacks {required_role.value} role in district {district_id}"
                )
        
        return True
    
    def validate_congregation_access(
        self,
        congregation_id: uuid.UUID,
        required_role: Role | None = None,
    ) -> bool:
        """
        Validiere Zugriff auf eine Gemeinde.
        
        Args:
            congregation_id: ID der Gemeinde
            required_role: Erforderliche Rolle (optional)
            
        Returns:
            True wenn Zugriff erlaubt
            
        Raises:
            TenantValidationError: Wenn Zugriff verweigert
        """
        current_district = TenantContext.get_district()
        current_user_sub = TenantContext.get_user_sub()
        is_superadmin = self._is_superadmin()
        
        # Superadmin hat Zugriff auf alle Gemeinden
        if is_superadmin:
            return True
        
        # Prüfe ob Gemeinde zum aktuellen Bezirk gehört
        # (Hier müsste die Zuordnung Gemeinde -> Bezirk geprüft werden)
        if not self._congregation_belongs_to_district(congregation_id, current_district):
            if self.audit_service:
                import asyncio
                asyncio.create_task(
                    self.audit_service.log_action(
                        action="ACCESS_DENIED",
                        resource_type="Congregation",
                        resource_id=congregation_id,
                        user_sub=current_user_sub,
                        error_message="Cross-tenant access attempt",
                        status="failed",
                    )
                )
            raise TenantValidationError(
                f"User {current_user_sub} cannot access congregation {congregation_id}"
            )
        
        # Prüfe Rolle
        if required_role:
            from app.adapters.auth.permissions import has_role_in_congregation
            if not has_role_in_congregation(current_user_sub, required_role, congregation_id):
                raise TenantValidationError(
                    f"User {current_user_sub} lacks {required_role.value} role in congregation {congregation_id}"
                )
        
        return True
    
    def _is_superadmin(self) -> bool:
        """Prüfe ob aktueller Nutzer Superadmin ist."""
        user_sub = TenantContext.get_user_sub()
        if user_sub:
            return user_sub.startswith("superadmin:")
        return False
    
    def _congregation_belongs_to_district(self, congregation_id: uuid.UUID, district_id: uuid.UUID) -> bool:
        """Prüfe ob Gemeinde zum Bezirk gehört."""
        # Hier müsste die Datenbank-Abfrage implementiert werden
        # Für jetzt: Annahme dass es eine Zuordnung gibt
        return True
```

### 7. Decorator für Tenant-Validierung

**Einfache Validierung mit Decorator:**

```python
# app/application/tenant_validation.py
from functools import wraps
from typing import Callable, TypeVar
import uuid

T = TypeVar('T')

def validate_tenant_district(
    district_id_param: str = "district_id",
    required_role: Role | None = None,
):
    """Decorator für Tenant-Validierung auf District-Ebene."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Extrahiere district_id
            district_id = kwargs.get(district_id_param)
            if isinstance(district_id, str):
                district_id = uuid.UUID(district_id)
            
            # Validiere
            service = TenantValidationService()
            service.validate_district_access(district_id, required_role)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def validate_tenant_congregation(
    congregation_id_param: str = "congregation_id",
    required_role: Role | None = None,
):
    """Decorator für Tenant-Validierung auf Congregation-Ebene."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Extrahiere congregation_id
            congregation_id = kwargs.get(congregation_id_param)
            if isinstance(congregation_id, str):
                congregation_id = uuid.UUID(congregation_id)
            
            # Validiere
            service = TenantValidationService()
            service.validate_congregation_access(congregation_id, required_role)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Beispielverwendung
@validate_tenant_district(district_id_param="district_id", required_role=Role.DISTRICT_ADMIN)
async def update_district_settings(district_id: uuid.UUID, settings: dict) -> District:
    # Implementierung
    pass
```

### 8. Integration mit bestehenden Routern

**Anpassung der bestehenden Router:**

```python
# app/adapters/api/routers/events.py
from app.application.tenant_validation import validate_tenant_district, validate_tenant_congregation
from app.domain.models.role import Role

@router.post("/events")
@validate_tenant_district(district_id_param="district_id", required_role=Role.PLANNER)
async def create_event(
    auth: CurrentUserWithMemberships,
    body: EventCreateRequest,
    session: DbSession,
) -> EventOut:
    # Tenant-Validierung wird automatisch durch Decorator durchgeführt
    # ... bestehende Implementierung
    pass

@router.get("/events/{event_id}")
async def get_event(
    auth: CurrentUserWithMemberships,
    event_id: uuid.UUID,
    session: DbSession,
) -> EventOut:
    # Tenant-Validierung durch Repository
    repo = SqlEventRepository(session)
    event = await repo.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Repository prüft automatisch Tenant-Zugehörigkeit
    return EventOut.from_orm(event)

@router.put("/events/{event_id}")
@validate_tenant_district(district_id_param="district_id", required_role=Role.PLANNER)
async def update_event(
    auth: CurrentUserWithMemberships,
    event_id: uuid.UUID,
    body: EventUpdateRequest,
    session: DbSession,
) -> EventOut:
    # Tenant-Validierung wird automatisch durchgeführt
    # ... bestehende Implementierung
    pass
```

### 9. Testing

**Test-Strategie:**

```python
# tests/integration/test_tenant_isolation.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.adapters.db.session import AsyncSessionLocal
from app.tenant import TenantContext

@pytest.mark.asyncio
async def test_cross_tenant_access_blocked():
    """Teste dass Cross-Tenant Zugriff blockiert wird."""
    client = TestClient(app)
    
    # Erstelle Nutzer in Bezirk A
    user_a = create_test_user(district_id=district_a_id)
    
    # Erstelle Event in Bezirk B
    event_b = create_test_event(district_id=district_b_id)
    
    # Versuche Event aus Bezirk B mit Nutzer aus Bezirk A zu lesen
    response = client.get(
        f"/api/v1/events/{event_b.id}",
        headers={"Authorization": f"Bearer {user_a.token}"},
    )
    
    # Sollte 403 oder 404 zurückgeben (nicht 200)
    assert response.status_code in [403, 404]

@pytest.mark.asyncio
async def test_superadmin_can_access_all_tenants():
    """Teste dass Superadmin alle Tenants sehen kann."""
    client = TestClient(app)
    
    # Erstelle Superadmin
    superadmin = create_test_superadmin()
    
    # Erstelle Event in Bezirk B
    event_b = create_test_event(district_id=district_b_id)
    
    # Superadmin sollte Event aus Bezirk B sehen können
    response = client.get(
        f"/api/v1/events/{event_b.id}",
        headers={"Authorization": f"Bearer {superadmin.token}"},
    )
    
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_rls_policies():
    """Teste dass RLS Policies funktionieren."""
    async with AsyncSessionLocal() as session:
        # Setze Tenant-Kontext
        token = TenantContext.set_context(
            tenant_id=district_a_id,
            district_id=district_a_id,
            user_sub="test_user",
        )
        
        try:
            # Führe Query aus
            result = await session.execute(
                select(Event).where(Event.id == event_b_id)
            )
            event = result.scalar()
            
            # Sollte None sein (Event gehört zu Bezirk B)
            assert event is None
            
        finally:
            TenantContext.reset(token)
```

## Risks / Trade-offs

| Risiko | Auswirkung | Mitigation |
|--------|------------|------------|
| **Performance Impact** | Erhöhte Latenz durch RLS | Optimierte Policies, Indizes |
| **Complexity** | Erhöhte Komplexität | Klare Abstraktion, gute Dokumentation |
| **Maintenance** | RLS Policies müssen gepflegt werden | Automatisierte Tests, Dokumentation |
| **Compatibility** | Probleme mit bestehenden Queries | Tenant-aware Repositories |
| **False Positives** | Legitime Zugriffe werden blockiert | Gute Fehlerbehandlung, Logging |

## Migration Plan

### Phase 1: Infrastruktur (2 Tage)
1. TenantContext implementieren
2. TenantMiddleware implementieren
3. PostgreSQL RLS Policies erstellen
4. RLS Middleware implementieren

### Phase 2: Tenant-Aware Repositories (3 Tage)
1. TenantAwareRepository Basis-Klasse erstellen
2. EventRepository anpassen
3. DistrictRepository anpassen
4. CongregationRepository anpassen
5. ServiceAssignmentRepository anpassen
6. CalendarIntegrationRepository anpassen

### Phase 3: Tenant Validation Service (2 Tage)
1. TenantValidationService implementieren
2. Decorators für Tenant-Validierung erstellen
3. In Router integrieren

### Phase 4: Testing (3 Tage)
1. Unit Tests für Tenant-Validierung
2. Integration Tests für RLS
3. End-to-End Tests für Cross-Tenant Zugriff
4. Performance Tests

### Phase 5: Rollout (1 Tag)
1. Staging Deployment
2. Monitoring einrichten
3. Fehlerbehandlung testen
4. Produktion Rollout

**Rollback:**
- RLS Policies können deaktiviert werden
- Tenant-Validierung kann über Feature-Flag deaktiviert werden
- Alte Code-Pfade bleiben erhalten

## Open Questions

1. Soll RLS für alle Tabellen aktiviert werden?
   - **Empfehlung:** Nur für Tenant-spezifische Tabellen

2. Soll Tenant-Isolation auf Application- oder Datenbank-Ebene priorisiert werden?
   - **Empfehlung:** Application-Ebene zuerst, dann Datenbank-Ebene

3. Wie mit komplexen Queries umgehen (Joins, Subqueries)?
   - **Empfehlung:** Tenant-aware Repositories verwenden

4. Soll Tenant-Isolation für Lese- und Schreiboperationen gelten?
   - **Empfehlung:** Ja, für beide

5. Wie mit Shared Data (z.B. System-Konfiguration) umgehen?
   - **Empfehlung:** Separate Tabellen ohne RLS
