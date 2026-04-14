# Test- und Coverage-Strategie

Dieses Dokument beschreibt, wie Testabdeckung im Projekt gemessen und bewertet wird.

## 1. Ziele

- Kritische Fachlogik ist durch Unit-Tests abgesichert.
- Sicherheits- und Berechtigungslogik hat hohe Testabdeckung.
- Integrationspunkte (DB, Sync, Auth) sind durch Integrationstests validiert.

## 2. Testebenen

- Unit: schnelle, isolierte Tests fuer Domain und Application Services.
- Integration: FastAPI + DB + relevante externe Adapter mit kontrollierter Umgebung.
- Frontend Unit/Component: Stores, Composables, zentrale Views/Komponenten.
- E2E: kritische End-to-End-Fluesse (insb. Login, geschuetzte Routen, Kernplanung).

## 3. Coverage-Messung

- Backend-Coverage wird in CI als XML erzeugt und an Codecov hochgeladen
  (siehe `.github/workflows/ci.yml`).
- Frontend-Tests laufen in CI; Coverage-Erweiterung kann schrittweise ergaenzt werden.

## 4. Mindestanforderungen (Policy)

- Neue sicherheitsrelevante oder berechtigungsrelevante Logik: Tests verpflichtend.
- Neue Domain-/Application-Logik ohne Tests ist nicht merge-faehig.
- Fuer bestehende Legacy-Bereiche gilt: bei Aenderungen "boy scout rule"
  (mindestens bestehende Testabdeckung nicht verschlechtern).

## 5. Empfohlene Zielwerte (inkrementell)

- Backend gesamt: >= 80% line coverage
- Kritische Module (Auth, RBAC, Sync): >= 90%
- Frontend Kernfluesse: testbasiert abgesichert, Coverage schrittweise ausbauen

Hinweis: Zielwerte sind Leitplanken. Verbindliche Gates koennen spaeter im CI
hart konfiguriert werden.
