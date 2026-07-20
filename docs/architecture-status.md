# Architekturstatus (Ist vs. Ziel)

> **Letztes Update:** Juli 2026 — aktualisiert basierend auf `docs/code-review-2026-07.md`

Diese Seite zeigt den aktuellen Stand gegenueber der Zielarchitektur aus OpenSpec.

Legende: ✅ umgesetzt · 🟡 teilweise · ❌ offen

## 1. Fachliche Kernfaehigkeiten

- Event-CRUD: ✅
- Dienstplan-Matrix (Lueckenanzeige): ✅
- Feiertags-Import: ✅
- ICS-Export mit Token-Typen: ✅
- Event-Verteilung (`applicability`): ✅

## 2. Architektur-Fundament

- Hexagonale Struktur (Domain/Application/Adapters): ✅
- PlanningSlot/PlanningSeries-Modell: ✅
- EventInstance (Soll/Ist-Trennung): ✅
- ExternalEventLink: ✅ (teilweise — Modell und Repository vorhanden)
- ExternalEventCandidate-Review: ❌ (Phase 2, Produktentscheidung ausstehend)

## 3. Security und Governance

- OIDC/PKCE-Login: ✅
- Rollenmodell dokumentiert: ✅
- RBAC-Guards vollstaendig in allen Services: ✅ (DRY-Konsolidierung abgeschlossen, siehe PR-4)
- Audit-Logging vollstaendig: ✅ (Middleware + Queue-Writer aktiv in main.py verdrahtet)
- Rate-Limiting oeffentlicher Endpunkte: ✅ (pfadspezifische Limits fuer `/api/v1/export/*` aktiv)

## 4. Sync und Robustheit

- Zyklischer Sync + Hash-Deduplizierung: ✅
- ExternalEventLink/Sync-Metadata: ✅
- Gehärtete Sync-State-Machine: ✅ (SyncState: CLEAN/DIRTY_INTERNAL/DIRTY_EXTERNAL/CONFLICT)

## 5. Self-Update (Automatic Version Update)

- SemVer-Parsing + GHCR-Tag-Abfrage: ✅
- In-Memory-Versionscache mit TTL: ✅
- Periodischer Celery-Task `check_version` (alle 6h): ✅
- `GET /api/v1/system/version` mit RBAC (admin): ✅
- `POST /api/v1/system/update` im `manual`-Modus: ✅
- `POST /api/v1/system/update` im `docker-socket`-Modus: ✅
- Update-Frontend-Banner mit Dismiss-Logik: ✅
- Release-Notes-Link: ✅

## 6. Non-Functional Baseline

- CI fuer Lint/Test/Build: ✅
- Security-Scans in CI: ✅
- Performance-SLOs verbindlich validiert: ❌

## 7. Referenzen

- Zielbild: `openspec/architecture/overview.md`
- Umsetzungsreihenfolge: `openspec/architecture/implementation-roadmap.md`
- Detailanalyse: `docs/improvement-proposals.md`
- Code-Review (Juli 2026): `docs/code-review-2026-07.md`
- Aktionsplan: `docs/code-review-2026-07-action-plan.md`
