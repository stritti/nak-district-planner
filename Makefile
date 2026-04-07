.PHONY: migrate seed seed-dry-run

migrate:
	cd services/backend && uv run alembic upgrade head

seed:
	cd services/backend && uv run python seed_testdata.py

seed-dry-run:
	cd services/backend && uv run python seed_testdata.py --dry-run
