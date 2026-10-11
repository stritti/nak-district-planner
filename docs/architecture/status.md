# Architekturstatus

> **Referenz nach v1.0.0 (10. Oktober 2026).** Hier stehen Architekturgrenzen und technische Schulden, nicht eine zweite Implementierungsroadmap oder ein RC-2-Gate.

## Dokumente mit maßgeblichem Inhalt

| Frage | Quelle |
| --- | --- |
| Was ist implementiert? | [OpenSpec-Baseline](https://github.com/stritti/nak-district-planner/tree/main/openspec/specs) |
| Was ist in Planung? | [Roadmap](/roadmap), [aktive Changes](https://github.com/stritti/nak-district-planner/tree/main/openspec/changes) |
| Welche Rollen gelten? | [Rollenkonzept](/roles) und [RBAC-Coverage](/rbac-coverage) |
| Welche Security-Grenzen gelten? | [Security Baseline](/security-baseline) |
| Wie wird betrieben? | [Production Runbook](/production-runbook), [Produktiv-Stack](/production-compose) |

## Architekturregel

```text
Domain <- Application <- Adapters / Composition
```

Neue Application-Use-Cases verwenden Ports und explizite Policies. Die Integration konkreter Adapter erfolgt an der Composition Boundary. Vorhandene Legacy-Ausnahmen sollten reduziert, nicht um weitere Ausnahmen ergänzt werden. Zielbild: [Architekturüberblick](https://github.com/stritti/nak-district-planner/blob/main/docs/architecture/overview.md).

## Technische Schulden

- Legacy-Importe aus Application/Celery, doppelte Generator-/Sync-Logik, veraltete Frontend-Helfer: [#474](https://github.com/stritti/nak-district-planner/issues/474).
- Berechtigungsvertrag und stabile Generierungsidentität für verschobene Serientermine: [#503](https://github.com/stritti/nak-district-planner/issues/503).
- Synchronisationsjobs und Fehlerpersistenz: [#470](https://github.com/stritti/nak-district-planner/issues/470).
- Container- und Restore-Härtung: [#472](https://github.com/stritti/nak-district-planner/issues/472).
- Authentifizierungs-Härtung: [#471](https://github.com/stritti/nak-district-planner/issues/471).

Die Issues sind offen und ihre Behebung wird nicht vorweggenommen. Die RC-2-Bestandsaufnahme ist über [Git history](https://github.com/stritti/nak-district-planner/blob/2b20473b3791370495a31384b58ce1b254371ab1/docs/architecture-status.md) dokumentiert.
