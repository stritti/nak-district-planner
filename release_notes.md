## [v0.27.2] - 2026-07-04

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
* fix: Unit-Tests an require_role_in_district() angepasst (8805894)
* fix: resolve alembic multi-head and FK name length issues (#202) (4619e48)
* fix: 0125 als e5a2-Parent statt depends_on — schließt Multiple-Head-Lücke (c6dc17a)
* fix: remove e5a2 from merge parents (already consumed by 0125 depends_on) (6d20f11)
* fix: make 0125 depend on e5a2 approval-status migration (d3555fd)
* fix: use Python AST for FK name length check (c5d090b)
* fix: resolve 5 pre-existing unit test failures (b467acc)
* fix: remove Depends() from auth params in notifications router (334f407)
* fix: let column definitions create enum types automatically in 0012 migration (2093069)
* fix: remove tail from alembic upgrade for full log output (24095f6)

### Other Changes
* Clean Code: Refactoring und DRY-Verbesserungen (#206) (aa695f9)
* Clean Code Skill hinzugefügt (9f14d85)
* Clean Code: Refactoring und DRY-Verbesserungen (d039cb9)
* chore: release v0.27.1 (e810d6e)
* test: coverage >80% mit Tests für Pydantic-Validatoren, Writer-Loop, MS-Connector, ServiceAssignment u.a. (3f030d9)
* docs: add ENUM type handling pattern to alembic skill doc (0fcb965)
* docs: add dependency ordering section to alembic skill (dd1f128)
* chore: release v0.27.0 (fad556f)
* chore: release v0.26.2 (3d4804f)
* chore: release v0.26.1 (402e69e)
