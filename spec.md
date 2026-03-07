# Projekt-Spezifikation: NAK Bezirksplaner (Web-App)

## 1. Vision & Zielbild

Eine webbasierte Planungsplattform für Neuapostolische Kirchenbezirke. Das System aggregiert Termine aus dezentralen Gemeindekalendern (Google, Microsoft, CalDAV, iCal), ermöglicht eine zentrale Dienstplanung (Gottesdienstleitung) auf Bezirksebene und stellt bereinigte Feeds für die Öffentlichkeit und Amtsträger bereit.

## 2. Technischer Stack

Frontend: Vue.js 3 (Composition API), Vite, Tailwind CSS, Pinia (State Management).

Backend: Python 3.11+, FastAPI (Asynchron), SQLAlchemy 2.0.

Datenbank: PostgreSQL 15+.

Task-Management: Redis + Celery (für asynchrone Kalender-Synchronisation).

Infrastruktur: Docker & Docker Compose.

Architektur-Pattern: Hexagonal Architecture (Ports & Adapters) im Backend.

## 3. Core Domain Modell

### 3.1 Mandanten

District (Bezirk): Root-Tenant.

Congregation (Gemeinde): Gehört zu einem Bezirk.

### 3.2 Kalender-Integration

CalendarIntegration:

type: GOOGLE, MICROSOFT, CALDAV, ICS.

credentials: Verschlüsseltes JSON (OAuth Tokens oder URL/Auth).

sync_interval: Intervall in Minuten.

capabilities: READ, WRITE, WEBHOOK.

### 3.3 Event & Planung

Event: Das Kalender-Objekt.

source: INTERNAL (im Tool erstellt) oder EXTERNAL (importiert).

status: DRAFT, PUBLISHED.

visibility: INTERNAL, PUBLIC.

audiences: Liste von Tags (z.B. "Amtsträger", "Jugend").

ServiceAssignment: Verknüpft einen "Gottesdienst"-Event mit einer Person.

event_id: Referenz zum Event.

leader_name: Name des Dienstleiters (oder ID einer Person).

status: OPEN, ASSIGNED, CONFIRMED.

## 4. Architektur-Leitplanken für den Agenten

Source of Truth: Externe Kalender werden lokal gespiegelt (Cache-Tabelle). Änderungen an externen Events im Tool müssen (falls möglich) zurückgeschrieben werden (Write-Back).

Idempotenz: Sync-Jobs müssen via Hash-Vergleich verhindern, dass Duplikate entstehen.

Hexagonal Design: Die Business-Logik (Dienstplanung) darf nicht direkt von der FastAPI oder SQLAlchemy abhängen. Nutze Interfaces (Abstract Base Classes) für Repositories und Kalender-Connectoren.

iCal Stabilität: UIDs in exportierten ICS-Feeds müssen über die Zeit stabil bleiben, damit Kalender-Apps nicht ständig neue Termine anzeigen.