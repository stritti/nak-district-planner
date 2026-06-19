## Context

Der NAK District Planner verwaltet sensible Planungsdaten für kirchliche Gemeinden. Ohne Audit-Logging können Änderungen nicht nachvollzogen werden, was Compliance- und Sicherheitsanforderungen verletzt.

Aktuell existierende Komponenten:
- PostgreSQL Datenbank mit SQLAlchemy ORM
- FastAPI Backend mit strukturierten Routern
- Celery für Hintergrundaufgaben
- OIDC-basierte Authentifizierung mit JWT-Tokens

## Goals / Non-Goals

**Goals:**
- Alle schreibenden Operationen auditierbar machen
- Unveränderliche Audit-Logs erstellen
- Performance-Impact minimieren (< 5%)
- Compliance-Anforderungen erfüllen (OWASP A09, CIS 8.1)
- Forensik-Unterstützung für Sicherheitsvorfälle

**Non-Goals:**
- Echtzeit-Alerting auf Basis von Audit-Logs (kann später hinzugefügt werden)
- Integration mit externen SIEM-Systemen (optional, nicht in Scope)
- Benutzeroberfläche für Audit-Log Analyse (kann später hinzugefügt werden)

## Decisions

### 1. Audit-Log Datenmodell

```python
# SQLAlchemy Model für Audit-Logs
from datetime import UTC, datetime
import uuid
from enum import Enum
from typing import Optional
import json

class AuditAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: uuid.UUID = Column(uuid.UUID, primary_key=True, default=uuid.uuid4)
    timestamp: datetime = Column(DateTime(timezone=True), default=datetime.now(UTC), index=True)
    
    # Wer
    user_sub: Optional[str] = Column(String(255), nullable=True, index=True)
    user_email: Optional[str] = Column(String(255), nullable=True)
    user_roles: Optional[list[str]] = Column(JSONB, nullable=True)
    
    # Was
    action: AuditAction = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type: str = Column(String(100), nullable=False, index=True)
    resource_id: Optional[uuid.UUID] = Column(uuid.UUID, nullable=True, index=True)
    
    # Wo
    district_id: Optional[uuid.UUID] = Column(uuid.UUID, nullable=True, index=True)
    congregation_id: Optional[uuid.UUID] = Column(uuid.UUID, nullable=True, index=True)
    
    # Details
    changes: Optional[dict] = Column(JSONB, nullable=True)  # Vorher/Nachher für UPDATE
    old_values: Optional[dict] = Column(JSONB, nullable=True)  # Gelöschte Werte
    new_values: Optional[dict] = Column(JSONB, nullable=True)  # Neue Werte
    
    # Kontext
    ip_address: Optional[str] = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent: Optional[str] = Column(String(500), nullable=True)
    request_id: Optional[str] = Column(String(100), nullable=True, index=True)
    
    # Status
    status: str = Column(String(20), default="success", index=True)  # success, failed
    error_message: Optional[str] = Column(String(1000), nullable=True)
    
    # Metadaten
    metadata: Optional[dict] = Column(JSONB, nullable=True)
    created_at: datetime = Column(DateTime(timezone=True), default=datetime.now(UTC))
```

**Indices:**
- `timestamp` für zeitbasierte Abfragen
- `user_sub` für Benutzer-spezifische Abfragen
- `action + resource_type` für Aktionsanalyse
- `resource_id` für Ressourcen-spezifische Abfragen
- `district_id` für Tenant-spezifische Abfragen
- `status` für Fehleranalyse
- `request_id` für Request-Tracing

### 2. Audit-Log Service Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  Audit Middleware │    │ Audit Decorator  │    │ Audit API    │ │
│  │  (automatisch)    │    │  (manuell)       │    │ (Abfragen)   │ │
│  └────────┬────────┘    └────────┬────────┘    └──────┬──────┘ │
│           │                      │                     │         │
│           └──────────────────────┼─────────────────────┘         │
│                                  │                                   │
│                                  ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    AuditLoggingService                         │ │
│  │  ┌─────────────────────────────────────────────────────────┐│ │
│  │  │ - log_action()                                          ││ │
│  │  │ - log_request()                                         ││ │
│  │  │ - log_auth_event()                                      ││ │
│  │  │ - query_logs()                                          ││ │
│  │  │ - cleanup_old_logs()                                    ││ │
│  │  └─────────────────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                  │                                   │
│                                  ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   PostgreSQL (audit_logs)                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Audit Middleware

**Automatische Erfassung von Requests:**

```python
# app/adapters/api/middleware/audit.py
from fastapi import Request
from starlette.responses import Response
from starlette.datastructures import Headers
from typing import Callable, Awaitable
import uuid
import json

class AuditMiddleware:
    def __init__(self, app, audit_service: AuditLoggingService):
        self.app = app
        self.audit_service = audit_service
        self.skip_paths = {"/api/health", "/api/v1/auth/oidc/discovery"}
        self.skip_methods = {"GET", "HEAD", "OPTIONS"}
        
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Skip non-auditable requests
        if request.url.path in self.skip_paths or request.method in self.skip_methods:
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Capture request context
        user_sub = getattr(request.state, "user_sub", None)
        user_email = getattr(request.state, "user_email", None)
        user_roles = getattr(request.state, "user_roles", None)
        district_id = getattr(request.state, "district_id", None)
        
        # Execute request
        response = await call_next(request)
        
        # Log request (only for authenticated users)
        if user_sub:
            action = self._map_method_to_action(request.method)
            resource_type = self._extract_resource_type(request.url.path)
            resource_id = self._extract_resource_id(request.url.path)
            
            await self.audit_service.log_request(
                request_id=request_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_sub=user_sub,
                user_email=user_email,
                user_roles=user_roles,
                district_id=district_id,
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                status="success" if response.status_code < 400 else "failed",
                error_message=None if response.status_code < 400 else "HTTP " + str(response.status_code),
                metadata={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                }
            )
        
        return response
        
    def _map_method_to_action(self, method: str) -> AuditAction:
        mapping = {
            "POST": AuditAction.CREATE,
            "PUT": AuditAction.UPDATE,
            "PATCH": AuditAction.UPDATE,
            "DELETE": AuditAction.DELETE,
        }
        return mapping.get(method, AuditAction.UPDATE)
        
    def _extract_resource_type(self, path: str) -> str:
        # Extrahiere Ressourcentyp aus Pfad
        parts = path.split("/")
        for part in parts:
            if part in ["events", "districts", "congregations", "leaders", "service-assignments"]:
                return part
        return "unknown"
        
    def _extract_resource_id(self, path: str) -> uuid.UUID | None:
        # Extrahiere UUID aus Pfad
        import re
        match = re.search(r'/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', path)
        if match:
            return uuid.UUID(match.group(1))
        return None
```

### 4. Audit Decorator

**Manuelles Logging für komplexe Operationen:**

```python
# app/application/audit.py
from functools import wraps
from typing import Callable, TypeVar, Any
import json
import uuid

T = TypeVar('T')

class AuditLoggingService:
    """Service für Audit-Logging Operationen."""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
        
    async def log_action(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        user_sub: str | None = None,
        user_email: str | None = None,
        user_roles: list[str] | None = None,
        district_id: uuid.UUID | None = None,
        congregation_id: uuid.UUID | None = None,
        changes: dict | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        status: str = "success",
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Erstelle einen Audit-Log Eintrag."""
        async with self.session_factory() as session:
            audit_log = AuditLog(
                timestamp=datetime.now(UTC),
                user_sub=user_sub,
                user_email=user_email,
                user_roles=user_roles,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                district_id=district_id,
                congregation_id=congregation_id,
                changes=changes,
                old_values=old_values,
                new_values=new_values,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                status=status,
                error_message=error_message,
                metadata=metadata,
            )
            session.add(audit_log)
            await session.commit()
    
    async def log_request(
        self,
        request_id: str,
        action: AuditAction,
        resource_type: str,
        resource_id: uuid.UUID | None = None,
        user_sub: str | None = None,
        user_email: str | None = None,
        user_roles: list[str] | None = None,
        district_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Erstelle einen Audit-Log Eintrag aus Request-Kontext."""
        await self.log_action(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_sub=user_sub,
            user_email=user_email,
            user_roles=user_roles,
            district_id=district_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
            metadata=metadata,
        )

def audit_action(
    action: AuditAction,
    resource_type: str,
    get_resource_id: Callable[..., uuid.UUID | None] | None = None,
    get_changes: Callable[..., dict | None] | None = None,
):
    """Decorator für Audit-Logging von Operationen."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Extrahiere Audit-Service aus Dependencies
            audit_service = kwargs.get("audit_service") or getattr(args[0], "audit_service", None)
            user_sub = kwargs.get("user_sub") or getattr(args[0], "user_sub", None)
            
            # Extrahiere Resource ID
            resource_id = None
            if get_resource_id:
                resource_id = get_resource_id(*args, **kwargs)
            
            # Extrahiere Changes
            changes = None
            if get_changes:
                changes = get_changes(*args, **kwargs)
            
            try:
                result = await func(*args, **kwargs)
                
                # Logge erfolgreiche Aktion
                if audit_service:
                    await audit_service.log_action(
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        user_sub=user_sub,
                        changes=changes,
                        status="success",
                    )
                
                return result
                
            except Exception as e:
                # Logge fehlgeschlagene Aktion
                if audit_service:
                    await audit_service.log_action(
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        user_sub=user_sub,
                        changes=changes,
                        status="failed",
                        error_message=str(e),
                    )
                raise
        
        return wrapper
    return decorator

# Beispielverwendung
@audit_action(
    action=AuditAction.CREATE,
    resource_type="Event",
    get_resource_id=lambda self, event_data: event_data.get("id"),
    get_changes=lambda self, event_data: {"title": event_data.get("title")},
)
async def create_event(self, event_data: dict) -> Event:
    event = Event.create(**event_data)
    await self.event_repo.save(event)
    return event
```

### 5. Audit API

**Endpunkte für Audit-Log Abfragen (nur Superadmin):**

```python
# app/adapters/api/routers/audit.py
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

@router.get("/logs")
async def list_audit_logs(
    auth: CurrentUserWithMemberships,
    session: DbSession,
    action: AuditAction | None = Query(None),
    resource_type: str | None = Query(None),
    resource_id: uuid.UUID | None = Query(None),
    user_sub: str | None = Query(None),
    district_id: uuid.UUID | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[AuditLogOut]:
    """Liste Audit-Logs (nur Superadmin)."""
    if not auth.user.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin Rechte erforderlich")
    
    audit_repo = SqlAuditLogRepository(session)
    logs = await audit_repo.list(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_sub=user_sub,
        district_id=district_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    
    return [AuditLogOut.from_orm(log) for log in logs]

@router.get("/logs/export")
async def export_audit_logs(
    auth: CurrentUserWithMemberships,
    session: DbSession,
    format: str = Query("csv", description="Export format: csv or json"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
) -> Response:
    """Exportiere Audit-Logs (nur Superadmin)."""
    if not auth.user.is_superadmin:
        raise HTTPException(status_code=403, detail="Superadmin Rechte erforderlich")
    
    audit_repo = SqlAuditLogRepository(session)
    logs = await audit_repo.list(
        start_date=start_date,
        end_date=end_date,
        limit=10000,  # Max 10k Einträge
    )
    
    if format == "csv":
        content = audit_repo.export_to_csv(logs)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="audit_logs.csv"'},
        )
    else:
        content = audit_repo.export_to_json(logs)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="audit_logs.json"'},
        )
```

### 6. Log Retention

**Automatische Bereinigung alter Logs:**

```python
# app/application/audit_retention.py
from datetime import UTC, datetime, timedelta
from app.adapters.db.repositories.audit_log import SqlAuditLogRepository

class AuditRetentionService:
    """Service für Audit-Log Retention."""
    
    def __init__(self, retention_days: int = 90):
        self.retention_days = retention_days
        
    async def cleanup_old_logs(self, session) -> int:
        """Lösche Logs älter als retention_days."""
        cutoff_date = datetime.now(UTC) - timedelta(days=self.retention_days)
        
        audit_repo = SqlAuditLogRepository(session)
        deleted_count = await audit_repo.delete_before(cutoff_date)
        
        return deleted_count

# Celery Task für regelmäßige Bereinigung
@celery.task
async def cleanup_audit_logs_task():
    """Celery Task zur Bereinigung alter Audit-Logs."""
    from app.adapters.db.session import AsyncSessionLocal
    from app.application.audit_retention import AuditRetentionService
    
    async with AsyncSessionLocal() as session:
        service = AuditRetentionService(retention_days=90)
        deleted_count = await service.cleanup_old_logs(session)
        
        logger.info(f"Audit log cleanup: {deleted_count} logs deleted")
        return deleted_count

# Schedule: Täglich um 02:00 Uhr
CELERY_BEAT_SCHEDULE = {
    "audit-log-cleanup": {
        "task": "app.application.audit_retention.cleanup_audit_logs_task",
        "schedule": crontab(hour=2, minute=0),
    },
}
```

### 7. Integration mit bestehenden Komponenten

**Anpassungen an bestehenden Repositories:**

```python
# Beispiel: Event Repository mit Audit-Logging
class SqlEventRepository:
    def __init__(self, session, audit_service: AuditLoggingService | None = None):
        self.session = session
        self.audit_service = audit_service
        
    async def save(self, event: Event) -> Event:
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        
        # Audit-Logging
        if self.audit_service:
            await self.audit_service.log_action(
                action=AuditAction.CREATE,
                resource_type="Event",
                resource_id=event.id,
                user_sub=getattr(event, "created_by", None),
                new_values=event.to_dict(),
            )
        
        return event
        
    async def update(self, event_id: uuid.UUID, updates: dict) -> Event | None:
        event = await self.get(event_id)
        if not event:
            return None
        
        # Speichere alte Werte für Audit
        old_values = event.to_dict()
        
        # Wende Updates an
        for key, value in updates.items():
            setattr(event, key, value)
        
        await self.session.commit()
        await self.session.refresh(event)
        
        # Audit-Logging
        if self.audit_service:
            changes = {k: v for k, v in updates.items() if old_values.get(k) != v}
            await self.audit_service.log_action(
                action=AuditAction.UPDATE,
                resource_type="Event",
                resource_id=event.id,
                user_sub=getattr(event, "updated_by", None),
                old_values=old_values,
                new_values=event.to_dict(),
                changes=changes,
            )
        
        return event
        
    async def delete(self, event_id: uuid.UUID) -> bool:
        event = await self.get(event_id)
        if not event:
            return False
        
        # Speichere Werte für Audit
        old_values = event.to_dict()
        
        await self.session.delete(event)
        await self.session.commit()
        
        # Audit-Logging
        if self.audit_service:
            await self.audit_service.log_action(
                action=AuditAction.DELETE,
                resource_type="Event",
                resource_id=event.id,
                user_sub=getattr(event, "deleted_by", None),
                old_values=old_values,
            )
        
        return True
```

### 8. Performance-Optimierungen

**Asynchrones Schreiben:**

```python
# Option 1: Asynchrone Queue für Audit-Logs
import asyncio
from collections import deque

class AsyncAuditLoggingService:
    def __init__(self, max_queue_size: int = 1000):
        self.queue = deque(maxlen=max_queue_size)
        self.lock = asyncio.Lock()
        self.running = False
        
    async def start(self):
        """Starte den Background Worker."""
        self.running = True
        asyncio.create_task(self._process_queue())
        
    async def stop(self):
        """Stoppe den Background Worker."""
        self.running = False
        await self._process_queue()  # Verarbeite Rest
        
    async def log_action(self, **kwargs):
        """Füge Log-Eintrag zur Queue hinzu."""
        async with self.lock:
            self.queue.append(kwargs)
            
    async def _process_queue(self):
        """Verarbeite die Queue im Hintergrund."""
        while self.running or self.queue:
            async with self.lock:
                if not self.queue:
                    await asyncio.sleep(0.1)
                    continue
                batch = list(self.queue)
                self.queue.clear()
            
            # Schreibe Batch in Datenbank
            async with self.session_factory() as session:
                for log_data in batch:
                    audit_log = AuditLog(**log_data)
                    session.add(audit_log)
                await session.commit()
                
            await asyncio.sleep(0.1)  # Throttle
```

### 9. Security Considerations

**Schutz der Audit-Logs:**

1. **Keine Löschung/Änderung:**
   - `audit_logs` Tabelle hat keine UPDATE/DELETE Trigger
   - Nur Superadmin kann Logs exportieren
   - Keine API-Endpunkte für Löschung von Logs

2. **Datenminimierung:**
   - Keine sensiblen Daten (Passwörter, Tokens) in Logs
   - Changes-Felder enthalten nur Metadaten, keine Credentials

3. **Zugriffskontrolle:**
   - Audit-Log API nur für Superadmin
   - Tenant-Isolation: Superadmin sieht alle Logs, andere Nutzer nur eigene

4. **Integrität:**
   - Audit-Logs werden sofort geschrieben (kein Caching)
   - Datenbank-Constraints verhindern Manipulation

## Risks / Trade-offs

| Risiko | Auswirkung | Mitigation |
|--------|------------|------------|
| **Performance Impact** | Erhöhte Latenz durch DB-Writes | Asynchrones Schreiben, Batching |
| **Storage Growth** | Große Datenmenge durch Logs | Retention Policy, Kompression |
| **Complexity** | Erhöhte Komplexität des Codes | Klare Abstraktion, gute Dokumentation |
| **Privacy Concerns** | Logs könnten persönliche Daten enthalten | Datenminimierung, Anonymisierung |
| **Data Loss** | Logs gehen bei DB-Fehler verloren | Transaktions-Logging, Retry-Mechanismus |

## Migration Plan

### Phase 1: Infrastruktur (1 Woche)
1. Erstelle `audit_logs` Tabelle
2. Implementiere `AuditLoggingService`
3. Implementiere Audit Middleware
4. Implementiere Audit Decorator
5. Füge Indizes hinzu

### Phase 2: Integration (2 Wochen)
1. Integriere Audit-Logging in Event Repository
2. Integriere in ServiceAssignment Repository
3. Integriere in CalendarIntegration Repository
4. Integriere in ExportToken Repository
5. Integriere in User/District/Congregation Repositories

### Phase 3: API & Retention (1 Woche)
1. Implementiere Audit-Log API Endpunkte
2. Implementiere Export-Funktionalität
3. Implementiere Retention Celery Task
4. Konfiguriere Celery Beat Schedule

### Phase 4: Testing & Rollout (1 Woche)
1. Unit Tests für Audit-Logging
2. Integration Tests
3. Performance Tests
4. Staging Deployment
5. Produktion Rollout

**Rollback:**
- Audit-Logging kann über Feature-Flag deaktiviert werden
- Alte Code-Pfade bleiben erhalten
- Datenbank-Migration ist reversibel

## Open Questions

1. Sollten Audit-Logs auch für Lese-Operationen erstellt werden?
   - **Empfehlung:** Nein, nur schreibende Operationen

2. Sollten Audit-Logs in separate Datenbank?
   - **Empfehlung:** Nein, gleiche DB aber separate Schema

3. Sollten Audit-Logs verschlüsselt werden?
   - **Empfehlung:** Nur sensible Felder (old_values/new_values bei Bedarf)

4. Sollten Audit-Logs an SIEM gesendet werden?
   - **Empfehlung:** Optional über Webhook

5. Wie mit Timezone-Umstellung umgehen?
   - **Empfehlung:** Immer UTC verwenden
