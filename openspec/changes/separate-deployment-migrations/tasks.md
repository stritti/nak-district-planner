## 1. Deployment

- [x] 1.1 One-Shot-Migration-Service ohne Tool-Profil betreiben.
- [x] 1.2 Backend und Worker auf erfolgreichen Migration-Service warten lassen.
- [x] 1.3 Owner-Credentials nur im Migration-Service laden.
- [x] 1.4 Alembic-Upgrade aus FastAPI-Lifespan entfernen.

## 2. Tests

- [x] 2.1 Test absichern, dass Runtime-Code kein `command.upgrade` ausfuehrt.
- [x] 2.2 Test absichern, dass Backend/Worker auf `service_completed_successfully` warten.
- [x] 2.3 Test absichern, dass `.env.docker.migrate` nicht in Runtime-Services geladen wird.

## 3. Verifikation

- [ ] 3.1 Backend Unit Tests und Coverage erfolgreich.
- [ ] 3.2 Compose-Konfiguration erfolgreich.
- [ ] 3.3 Migration Graph & FK Names erfolgreich.
- [ ] 3.4 Encrypted Backup & Isolated Restore erfolgreich.