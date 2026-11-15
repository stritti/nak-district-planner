.PHONY: migrate seed seed-dry-run seed-reset-demo osv-scan

# Runs the one-shot migrate service, which alone loads the owner credentials (.env.db).
migrate:
	docker compose run --no-deps --rm --build migrate

seed:
	cd services/backend && uv run python seed_testdata.py

seed-dry-run:
	cd services/backend && uv run python seed_testdata.py --dry-run

seed-reset-demo:
	cd services/backend && uv run python seed_testdata.py --reset-demo

# Scans all lockfiles (backend uv.lock, frontend + root bun.lock) against the OSV
# database, same as the "OSV Dependency Scan (osv-scanner)" job in security.yml.
osv-scan:
	docker run --rm -v "$(CURDIR):/src" -w /src ghcr.io/google/osv-scanner:v2.7.1 scan source -r ./
