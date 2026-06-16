.PHONY: lint format typecheck test check up down logs precommit seed

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check src/ tests/ --fix

typecheck:
	uv run mypy src/

test:
	uv run pytest

check: lint typecheck test

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

precommit:
	uv run pre-commit install

seed:
	uv run python scripts/seed.py
