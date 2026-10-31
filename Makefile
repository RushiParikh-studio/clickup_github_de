export DBT_PROFILES_DIR := $(CURDIR)/dbt

.PHONY: ci
ci:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest -q
	cd dbt && uv run dbt build --target ci
