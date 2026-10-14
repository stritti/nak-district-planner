## Context

Das Backend folgt Hexagonal Architecture. Kalender-Provider-Logik muss hinter einem Interface (`CalendarConnector` ABC) liegen, damit Sync-Tasks und Tests Provider-agnostisch arbeiten können. Credentials (OAuth-Tokens, Passwörter) dürfen nie im Klartext in der Datenbank stehen.

Aktueller Stand: Domain-Modelle und FastAPI-Stub sind vorhanden (`services/backend/app/`). CalendarIntegration-Tabelle und Provider-Adapter existieren noch nicht.

## Goals / Non-Goals

**Goals:**
- `CalendarConnector` ABC mit Methoden `authenticate()`, `list_events()`, `get_event()`, `write_event()` (write optional je nach `capabilities`)
- Konkreter `ICalConnector` (ICS-URL, read-only) als erste Implementierung
- `CalendarIntegration`-SQLAlchemy-Modell + Alembic-Migration
- Fernet-basierte Credential-Verschlüsselung als Decorator am Repository-Layer
- REST-Endpunkte für CRUD der CalendarIntegration
- OAuth-Callback-Endpoint (Skeleton für Google/Microsoft — vollständige OAuth-Flows in Phase 2)

**Non-Goals:**
- Vollständige Google- und Microsoft-OAuth-Flows (Phase 2)
- Write-Back an externe Provider
- CalDAV-Provider-Implementierung (Phase 2)

## Decisions

### Strategy-Pattern via ABC
**Entscheidung:** `CalendarConnector` als Abstract Base Class in `domain/ports/calendar_connector.py`.

Alternativen: Protocol (duck typing) wäre simpler, aber ABC erzwingt die Implementierung aller Methoden zur Definitionszeit — frühere Fehlermeldung bei unvollständigen Adaptern.

### Fernet-Verschlüsselung
**Entscheidung:** `cryptography.fernet.Fernet` mit einem aus `ENCRYPTION_KEY` abgeleiteten Key (Base64-URL-safe, 32 Byte). Der Repository-Decorator ver-/entschlüsselt transparent vor jedem Read/Write.

Alternativen: Vault, KMS (zu komplex für MVP), pgcrypto (verschiebt die Schlüsselverwaltung in die DB).

Risiko: Key-Rotation erfordert Re-Encryption aller gespeicherten Credentials — Migrationspfad muss separat geplant werden.

### ICalConnector als erste Implementierung
**Entscheidung:** ICS-URL-Connector (read-only) wird als erster konkreter Adapter implementiert, da er keine OAuth-Infrastruktur benötigt.

**Begründung:** Ermöglicht sofortiges End-to-End-Testing des Sync-Flows (UC-02), ohne OAuth-Infrastruktur aufsetzen zu müssen.

## Risks / Trade-offs

- [Risiko] `ENCRYPTION_KEY` verloren → alle Credentials unlesbar → **Mitigation:** Key in Secrets-Management-System (z. B. Docker Secret), Backup obligatorisch dokumentieren
- [Trade-off] Strategy-Pattern erhöht Komplexität bei nur einer konkreten Implementierung → akzeptiert, da UC-02 direkt auf dem ABC aufbaut

## Migration Plan

1. Alembic-Migration: Tabelle `calendar_integration` anlegen
2. `ICalConnector` implementieren und testen
3. Encryption-Decorator hinzufügen
4. REST-Endpunkte aktivieren
5. Rollback: Migration `downgrade` entfernt die Tabelle; kein Impact auf bestehende Events-Tabelle
