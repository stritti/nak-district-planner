# Architekturstatus (Ist vs. Ziel)

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
- PlanningSlot/PlanningSeries-Modell: ❌
- EventInstance (Soll/Ist-Trennung): ❌
- ExternalEventCandidate-Review: ❌

## 3. Security und Governance

- OIDC/PKCE-Login: ✅
- Rollenmodell dokumentiert: ✅
- RBAC-Guards vollstaendig in allen Services: 🟡
- Audit-Logging vollstaendig: 🟡
- Rate-Limiting oeffentlicher Endpunkte: ❌

## 4. Sync und Robustheit

- Zyklischer Sync + Hash-Deduplizierung: ✅
- ExternalEventLink/Sync-Metadata: ❌
- Gehärtete Sync-State-Machine: ❌

## 5. Non-Functional Baseline

- CI fuer Lint/Test/Build: ✅
- Security-Scans in CI: ✅
- Performance-SLOs verbindlich validiert: ❌

## 6. Referenzen

- Zielbild: `openspec/architecture/overview.md`
- Umsetzungsreihenfolge: `openspec/architecture/implementation-roadmap.md`
- Detailanalyse: `docs/improvement-proposals.md`
