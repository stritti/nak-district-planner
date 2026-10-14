.PHONY: migrate seed seed-dry-run

# Runs the one-shot migrate service, which alone loads the owner credentials (.env.db).
migrate:
	docker compose run --no-deps --rm --build migrate

seed:
	cd services/backend && uv run python seed_testdata.py

seed-dry-run:
	cd services/backend && uv run python seed_testdata.py --dry-run
