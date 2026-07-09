## [v0.27.5] - 2026-07-09

### Features
* feat(m3): remove legacy Event model — EventInstance + ExternalEventLink + Sync Härtung (#190) (e99a840)
* feat(matrix): complete M1 frontend integration with deviation display (#188) (75a13f8)
* feat: tenant isolation (SEC-020, SEC-021) (e197af9)
* feat(matrix): implement PlanningSeries slot generation and deviation display (M1) (#187) (3eb157f)
* feat(security): implement audit logging (SEC-009) (753a502)
* Merge pull request #172 from stritti/feature/security-rate-limiting-sec-016 (dbd4806)
* Merge pull request #186 from stritti/feat/sync-status-card (3a0a7ae)
* Merge pull request #185 from stritti/feat/toast-confirm-dialogs (8a50676)
* Merge pull request #184 from stritti/feat/health-check-endpoint (9a5df96)
* Merge pull request #174 from stritti/feature/matrix-rendering-migration-1-1 (55355e8)

### Bug Fixes
* Merge pull request #209 from stritti/fix/leaders-link-self-rbac-gap (8824da2)
* fix: congregation-scoped users können self-link weiter nutzen (7116acc)
* fix(security): RBAC-Guard für leaders link-self Endpoints (B-1) (9cb06f1)
* Merge pull request #207 from stritti/fix/pip-audit-cve-joserfc (5e26c41)
* fix: joserfc auf 1.7.3 aktualisiert — CVE-2026-48990, CVE-2026-49852 behoben (a920f40)
* fix: Unit-Tests an require_role_in_district() angepasst (8805894)
* fix: resolve alembic multi-head and FK name length issues (#202) (4619e48)
* fix: 0125 als e5a2-Parent statt depends_on — schließt Multiple-Head-Lücke (c6dc17a)
* fix: remove e5a2 from merge parents (already consumed by 0125 depends_on) (6d20f11)
* fix: make 0125 depend on e5a2 approval-status migration (d3555fd)

### Other Changes
* Merge pull request #194 from stritti/dependabot/uv/services/backend/sqlalchemy-asyncio--gte-2.0.51 (02b6fc1)
* chore: release v0.27.4 (cf8c23e)
* build(deps): Update sqlalchemy[asyncio] requirement in /services/backend (8fef6d9)
* chore: release v0.27.3 (1d10135)
* chore: release v0.27.2 (8d7df18)
* Clean Code: Refactoring und DRY-Verbesserungen (#206) (aa695f9)
* Clean Code Skill hinzugefügt (9f14d85)
* Clean Code: Refactoring und DRY-Verbesserungen (d039cb9)
* chore: release v0.27.1 (e810d6e)
* test: coverage >80% mit Tests für Pydantic-Validatoren, Writer-Loop, MS-Connector, ServiceAssignment u.a. (3f030d9)
