## Why

Der RC-1-Code enthaelt noch mehrere historisch gewachsene Abhaengigkeiten vom Application-Layer zu konkreten Adaptern und vereinzelt direkt zu SQLAlchemy. Ein vollstaendiger Port/Adapter-Umbau waere fuer RC-2 zu breit, neue Architektur-Schulden duerfen aber nicht mehr unbemerkt hinzukommen. Gleichzeitig sind Release-Metadaten und Betriebsdokumentation teilweise nicht mehr deckungsgleich mit dem tatsaechlichen RC-Stand.

## What Changes

- Ein AST-basierter Architekturtest friert bestehende `app.application -> app.adapters`- und direkte SQLAlchemy-Abhaengigkeiten mit einer expliziten Legacy-Allowlist ein.
- Neue Application-Module muessen Infrastruktur ueber Domain-Ports/Interfaces beziehen; die Legacy-Allowlist darf nicht erweitert werden.
- Veraltete Allowlist-Eintraege schlagen ebenfalls fehl, damit refaktorierte Altlasten aus der Liste entfernt werden.
- FastAPI bezieht seine API-Version aus derselben zentralen Paketversion wie Health- und Versionsendpunkte.
- Production Runbook, Architektur- und Security-Status werden auf die RC-2-Vertrauensgrenzen und Required Checks konsolidiert.
- Abgeschlossene OpenSpec-Changes werden aus dem aktiven Bereich archiviert, ohne ihre Historie zu verlieren.

## Capabilities

### Modified Capabilities

- `backend-architecture`: Application-Code darf keine neuen konkreten Infrastrukturabhaengigkeiten einfuehren.
- `release-readiness`: Runtime-Version und Betriebsdokumentation muessen den deployten RC-Stand widerspiegeln.

## Impact

- Bestehende Legacy-Imports bleiben fuer RC-2 zulaessig, sind aber technisch sichtbar und koennen nur reduziert, nicht still erweitert werden.
- Groessere Port/Adapter-Refactorings bleiben fuer nachfolgende, kleine PRs moeglich.
- Neue Application-Services muessen ihre Infrastrukturabhaengigkeiten von Beginn an hinter Ports modellieren.
